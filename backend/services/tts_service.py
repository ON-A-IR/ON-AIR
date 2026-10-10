import json
import os
import re
import subprocess
import uuid
import wave
from pathlib import Path
from urllib import error, request


ROOT_DIR = Path(__file__).resolve().parents[2]
STATIC_AUDIO_DIR = ROOT_DIR / "backend" / "static" / "audio"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"


class TtsError(RuntimeError):
    pass


def export_mp3(audio_url: str) -> Path:
    prefix = "/static/audio/"
    if not audio_url.startswith(prefix):
        raise TtsError("잘못된 음성 파일 경로입니다.")
    filename = audio_url[len(prefix):]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.(wav|mp3)", filename):
        raise TtsError("잘못된 음성 파일 이름입니다.")
    source = (STATIC_AUDIO_DIR / filename).resolve()
    if source.parent != STATIC_AUDIO_DIR.resolve() or not source.is_file():
        raise TtsError("음성 파일이 없습니다. 음성을 다시 생성해주세요.")
    if source.suffix == ".mp3":
        return source
    target = source.with_suffix(".mp3")
    if target.is_file() and target.stat().st_size:
        return target
    temporary = target.with_name(f"{target.stem}.{uuid.uuid4().hex}.tmp.mp3")
    try:
        import imageio_ffmpeg
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-y", "-i", str(source),
            "-vn", "-codec:a", "libmp3lame", "-b:a", "128k", str(temporary)],
            check=True, capture_output=True, timeout=180)
        temporary.replace(target)
        return target
    except (ImportError, OSError, subprocess.SubprocessError) as exc:
        raise TtsError("MP3 변환에 실패했습니다. 변환 도구 설치 상태를 확인해주세요.") from exc
    finally:
        temporary.unlink(missing_ok=True)


SPEAKER_LINE_RE = re.compile(r"^\s*([^:\[\]\r\n]{1,40})\s*:\s*(.+?)\s*$")


def load_dotenv() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _speech_turns(script: str) -> list[tuple[str, str]]:
    """Extract dialogue turns while keeping speaker names for Piper routing."""
    turns: list[tuple[str, str]] = []
    current_index: int | None = None

    for raw_line in script.splitlines():
        line = re.sub(r"^\s*\[[^\]]+\]\s*", "", raw_line).strip()
        if not line:
            continue

        match = SPEAKER_LINE_RE.match(line)
        if match:
            speaker = match.group(1).strip()
            text = match.group(2).strip()
            if text:
                turns.append((speaker, text))
                current_index = len(turns) - 1
            continue

        if current_index is None:
            turns.append(("", line))
            current_index = 0
        else:
            speaker, text = turns[current_index]
            turns[current_index] = (speaker, f"{text} {line}")

    return [(speaker, re.sub(r"\s+", " ", text).strip()) for speaker, text in turns if text.strip()]


def script_for_tts(script: str) -> str:
    """Remove section markers and host labels before single-voice speech."""
    return " ".join(text for _, text in _speech_turns(script)).strip()


def safe_audio_name(title: str, extension: str) -> tuple[str, Path]:
    STATIC_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    safe_title = re.sub(r"[^a-zA-Z0-9_-]+", "-", title).strip("-")[:40] or "broadcast"
    filename = f"{safe_title}-{uuid.uuid4().hex[:10]}.{extension}"
    output_path = STATIC_AUDIO_DIR / filename
    return filename, output_path


def create_sapi_speech_file(script: str, title: str = "broadcast") -> str:
    filename, output_path = safe_audio_name(title, "wav")
    text_path = output_path.with_suffix(".txt")
    script_path = output_path.with_suffix(".ps1")
    text_path.write_text(script_for_tts(script), encoding="utf-8")

    command = r"""
param([string]$TextPath, [string]$OutputPath)
$text = Get-Content -LiteralPath $TextPath -Raw -Encoding UTF8
$voice = New-Object -ComObject SAPI.SpVoice
$stream = New-Object -ComObject SAPI.SpFileStream
$stream.Open($OutputPath, 3, $false)
$voice.AudioOutputStream = $stream
$voice.Rate = -1
$voice.Volume = 100
[void]$voice.Speak($text)
$stream.Close()
"""
    script_path.write_text(command, encoding="utf-8")

    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                str(text_path),
                str(output_path),
            ],
            cwd=str(ROOT_DIR),
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.CalledProcessError as exc:
        raise TtsError(f"Windows SAPI TTS failed: {exc.stderr or exc.stdout}") from exc
    except FileNotFoundError as exc:
        raise TtsError("PowerShell was not found for Windows SAPI TTS.") from exc
    finally:
        text_path.unlink(missing_ok=True)
        script_path.unlink(missing_ok=True)

    if not output_path.exists() or output_path.stat().st_size <= 44:
        output_path.unlink(missing_ok=True)
        raise TtsError("Windows SAPI did not create a valid audio file. Run the backend with normal Windows user permissions.")

    return f"/static/audio/{filename}"


def _piper_speaker_count(model_path: Path, config_path: str) -> int:
    metadata_path = Path(config_path) if config_path else Path(f"{model_path}.json")
    if not metadata_path.exists():
        return 1

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        return max(1, int(metadata.get("num_speakers", 1)))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return 1


def _piper_emotion_args(tone: str, broadcast_format: str) -> list[str]:
    """Apply small prosody changes; Piper KSS does not have native emotion labels."""
    presets = {
        "casual": (1.00, 0.70, 0.80),
        "formal": (1.06, 0.58, 0.72),
        "cheerful": (0.91, 0.80, 0.88),
        "calm": (1.10, 0.55, 0.68),
    }
    length_scale, noise_scale, noise_w = presets.get(tone, presets["casual"])

    format_adjustments = {
        "summary": (-0.03, 0.00, 0.00),
        "critique": (0.03, -0.04, -0.03),
        "debate": (-0.05, 0.04, 0.04),
    }
    length_adjustment, noise_adjustment, noise_w_adjustment = format_adjustments.get(
        broadcast_format,
        (0.00, 0.00, 0.00),
    )

    return [
        "--length_scale",
        f"{max(0.82, min(1.22, length_scale + length_adjustment)):.3f}",
        "--noise_scale",
        f"{max(0.45, min(0.90, noise_scale + noise_adjustment)):.3f}",
        "--noise_w",
        f"{max(0.55, min(1.00, noise_w + noise_w_adjustment)):.3f}",
    ]


def _piper_command(
    piper_path: Path,
    model_path: Path,
    output_path: Path,
    piper_config: str,
    piper_espeak_data: str,
    speaker: str | None = None,
    tone: str = "casual",
    broadcast_format: str = "deep_dive",
) -> list[str]:
    command = [
        str(piper_path),
        "--model",
        str(model_path),
        "--output_file",
        str(output_path),
    ]

    if piper_config:
        config_path = Path(piper_config)
        if not config_path.exists():
            raise TtsError(f"Piper config was not found: {config_path}")
        command.extend(["--config", str(config_path)])

    if piper_espeak_data:
        espeak_data_path = Path(piper_espeak_data)
        if not espeak_data_path.exists():
            raise TtsError(f"Piper eSpeak data directory was not found: {espeak_data_path}")
        command.extend(["--espeak_data", str(espeak_data_path)])

    if speaker is not None and speaker.strip():
        command.extend(["--speaker", speaker.strip()])

    command.extend(_piper_emotion_args(tone, broadcast_format))
    return command


def _run_piper(command: list[str], text: str, output_path: Path) -> None:
    try:
        subprocess.run(
            command,
            input=text,
            cwd=str(ROOT_DIR),
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=180,
        )
    except subprocess.CalledProcessError as exc:
        output_path.unlink(missing_ok=True)
        raise TtsError(f"Piper TTS failed: {exc.stderr or exc.stdout}") from exc
    except FileNotFoundError as exc:
        output_path.unlink(missing_ok=True)
        raise TtsError("Piper executable could not be started.") from exc

    if not output_path.exists() or output_path.stat().st_size <= 44:
        output_path.unlink(missing_ok=True)
        raise TtsError("Piper did not create a valid audio file.")


def _join_wav_files(parts: list[Path], output_path: Path) -> None:
    if not parts:
        raise TtsError("Piper did not create any dialogue audio.")

    try:
        with wave.open(str(parts[0]), "rb") as first:
            channels = first.getnchannels()
            sample_width = first.getsampwidth()
            frame_rate = first.getframerate()
            compression = first.getcomptype()
            frames = [first.readframes(first.getnframes())]

        if compression != "NONE":
            raise TtsError("Piper returned a compressed WAV format that cannot be mixed.")

        silence = b"\x00" * int(frame_rate * 0.12) * channels * sample_width
        for part in parts[1:]:
            with wave.open(str(part), "rb") as current:
                if (
                    current.getnchannels() != channels
                    or current.getsampwidth() != sample_width
                    or current.getframerate() != frame_rate
                    or current.getcomptype() != compression
                ):
                    raise TtsError("Piper speaker segments have incompatible audio formats.")
                frames.extend([silence, current.readframes(current.getnframes())])

        with wave.open(str(output_path), "wb") as joined:
            joined.setnchannels(channels)
            joined.setsampwidth(sample_width)
            joined.setframerate(frame_rate)
            joined.writeframes(b"".join(frames))
    except (OSError, wave.Error) as exc:
        raise TtsError(f"Piper audio segments could not be joined: {exc}") from exc


def create_piper_speech_file(
    script: str,
    title: str = "broadcast",
    tone: str = "casual",
    broadcast_format: str = "deep_dive",
) -> str:
    piper_exe = os.environ.get("PIPER_EXE", "").strip()
    piper_model = os.environ.get("PIPER_MODEL", "").strip()

    if not piper_exe or not piper_model:
        raise TtsError("PIPER_EXE and PIPER_MODEL must be set.")

    piper_path = Path(piper_exe)
    model_path = Path(piper_model)
    if not piper_path.exists():
        raise TtsError(f"Piper executable was not found: {piper_path}")
    if not model_path.exists():
        raise TtsError(f"Piper model was not found: {model_path}")

    filename, output_path = safe_audio_name(title, "wav")
    piper_config = os.environ.get("PIPER_CONFIG", "").strip()
    piper_espeak_data = os.environ.get("PIPER_ESPEAK_DATA", "").strip()
    speaker_count = _piper_speaker_count(model_path, piper_config)
    turns = _speech_turns(script)
    speaker_names = list(dict.fromkeys(speaker for speaker, _ in turns if speaker))

    if len(speaker_names) > 2:
        output_path.unlink(missing_ok=True)
        raise TtsError("현재 라디오 TTS는 최대 두 명의 진행자만 지원합니다.")

    if speaker_count < 2 or len(speaker_names) < 2:
        # The bundled Korean KSS model is single-speaker. Keep the original
        # Piper voice for both hosts instead of falling back to Windows SAPI.
        piper_speaker = os.environ.get("PIPER_SPEAKER", "").strip() or None
        command = _piper_command(
            piper_path,
            model_path,
            output_path,
            piper_config,
            piper_espeak_data,
            piper_speaker,
            tone,
            broadcast_format,
        )
        _run_piper(command, script_for_tts(script), output_path)
        return f"/static/audio/{filename}"

    speaker_a = os.environ.get("PIPER_SPEAKER_A", "0").strip()
    speaker_b = os.environ.get("PIPER_SPEAKER_B", "1").strip()
    speaker_ids = [speaker_a, speaker_b]
    speaker_index = {name: index for index, name in enumerate(speaker_names[:2])}
    parts: list[Path] = []

    try:
        for index, (speaker_name, text) in enumerate(turns):
            part_path = output_path.with_name(f"{output_path.stem}.part-{index}.wav")
            part_speaker = speaker_ids[speaker_index.get(speaker_name, 0)]
            command = _piper_command(
                piper_path,
                model_path,
                part_path,
                piper_config,
                piper_espeak_data,
                part_speaker,
                tone,
                broadcast_format,
            )
            _run_piper(command, text, part_path)
            parts.append(part_path)

        _join_wav_files(parts, output_path)
    except TtsError:
        output_path.unlink(missing_ok=True)
        raise
    finally:
        for part in parts:
            part.unlink(missing_ok=True)

    return f"/static/audio/{filename}"


def create_elevenlabs_speech_file(script: str, title: str = "broadcast") -> str:
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise TtsError("ELEVENLABS_API_KEY is not set.")

    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": script_for_tts(script),
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.48,
            "similarity_boost": 0.78,
            "style": 0.25,
            "use_speaker_boost": True,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        },
    )

    try:
        with request.urlopen(req, timeout=90) as response:
            audio = response.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise TtsError(f"ElevenLabs request failed: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise TtsError(f"ElevenLabs network error: {exc.reason}") from exc

    filename, output_path = safe_audio_name(title, "mp3")
    output_path.write_bytes(audio)
    return f"/static/audio/{filename}"


def create_speech_file(
    script: str,
    title: str = "broadcast",
    tone: str = "casual",
    broadcast_format: str = "deep_dive",
) -> str:
    load_dotenv()

    provider = os.environ.get("TTS_PROVIDER", "auto").strip().lower()
    if provider == "piper":
        return create_piper_speech_file(script, title, tone, broadcast_format)
    if provider == "elevenlabs":
        return create_elevenlabs_speech_file(script, title)
    if provider in {"sapi", "windows", "local"}:
        return create_sapi_speech_file(script, title)

    if os.environ.get("PIPER_EXE") and os.environ.get("PIPER_MODEL"):
        try:
            return create_piper_speech_file(script, title, tone, broadcast_format)
        except TtsError:
            pass

    if os.environ.get("ELEVENLABS_API_KEY"):
        return create_elevenlabs_speech_file(script, title)

    return create_sapi_speech_file(script, title)


def get_tts_provider_label() -> str:
    load_dotenv()

    provider = os.environ.get("TTS_PROVIDER", "auto").strip().lower()
    if provider == "piper":
        return "Piper"
    if provider == "elevenlabs":
        return "ElevenLabs"
    if provider in {"sapi", "windows", "local"}:
        return "Windows SAPI"
    if os.environ.get("PIPER_EXE") and os.environ.get("PIPER_MODEL"):
        return "Piper"
    if os.environ.get("ELEVENLABS_API_KEY"):
        return "ElevenLabs"
    return "Windows SAPI"
