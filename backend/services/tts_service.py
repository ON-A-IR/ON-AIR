import json
import os
import re
import subprocess
import sys
import uuid
import wave
from functools import lru_cache
from threading import Lock
from tempfile import TemporaryDirectory
from array import array
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
    """Extract dialogue turns while keeping speaker names for voice routing."""
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


def _piper_text(text: str) -> str:
    pronunciations = {"AI": "에이아이", "API": "에이피아이", "CPU": "씨피유", "GPU": "지피유", "GPS": "지피에스", "LLM": "엘엘엠", "SAE": "에스에이이", "TTS": "티티에스", "LIDAR": "라이다"}
    for abbreviation, spoken in pronunciations.items():
        text = re.sub(rf"(?<![A-Za-z]){abbreviation}(?![A-Za-z])", spoken, text)
    text = re.sub(r"(?<=\d)\s*%", " 퍼센트", text)
    text = text.replace("…", ". ")
    text = re.sub(r"\.{3,}", ". ", text)
    text = re.sub(r"([!?])\1+", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _soften_edges(frames: bytes, channels: int, sample_width: int, frame_rate: int) -> bytes:
    if sample_width != 2:
        return frames
    samples = array("h", frames)
    if sys.byteorder != "little":
        samples.byteswap()
    count = len(samples) // channels
    fade = min(int(frame_rate * 0.005), count // 2)
    for frame in range(fade):
        gain = frame / max(1, fade)
        for channel in range(channels):
            for index in (frame * channels + channel, (count - frame - 1) * channels + channel):
                samples[index] = int(samples[index] * gain)
    if sys.byteorder != "little":
        samples.byteswap()
    return samples.tobytes()


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
    command.extend(["--sentence_silence", "0.16"])
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


def _trim_edge_silence(frames: bytes, channels: int, sample_width: int, frame_rate: int) -> bytes:
    if sample_width != 2:
        return frames
    samples = array("h", frames)
    if sys.byteorder != "little":
        samples.byteswap()
    # Keep a quiet margin so breaths and unvoiced consonants are not cut off.
    first = next((i for i, value in enumerate(samples) if abs(value) > 64), None)
    if first is None:
        return frames
    last = len(samples) - 1 - next(i for i, value in enumerate(reversed(samples)) if abs(value) > 64)
    margin = int(frame_rate * .08)
    start = max(0, first // channels - margin) * channels * sample_width
    end = min(len(samples) // channels, last // channels + margin + 1) * channels * sample_width
    return frames[start:end]


def _join_wav_files(parts: list[Path], output_path: Path, pauses: list[float] | None = None) -> None:
    if not parts:
        raise TtsError("TTS did not create any dialogue audio.")
    if pauses is not None and (len(pauses) != len(parts) - 1 or any(not 0 <= gap <= 1 for gap in pauses)):
        raise TtsError("대사 사이 간격 설정이 올바르지 않습니다.")

    try:
        with wave.open(str(parts[0]), "rb") as first:
            channels = first.getnchannels()
            sample_width = first.getsampwidth()
            frame_rate = first.getframerate()
            compression = first.getcomptype()
            first_frames = first.readframes(first.getnframes())
            if pauses is not None:
                first_frames = _trim_edge_silence(first_frames, channels, sample_width, frame_rate)
            frames = [_soften_edges(first_frames, channels, sample_width, frame_rate)]

        if compression != "NONE":
            raise TtsError("TTS returned a compressed WAV format that cannot be mixed.")

        for index, part in enumerate(parts[1:]):
            gap = pauses[index] if pauses is not None else .12
            silence = b"\x00" * int(frame_rate * gap) * channels * sample_width
            with wave.open(str(part), "rb") as current:
                if (
                    current.getnchannels() != channels
                    or current.getsampwidth() != sample_width
                    or current.getframerate() != frame_rate
                    or current.getcomptype() != compression
                ):
                    raise TtsError("TTS speaker segments have incompatible audio formats.")
                current_frames = current.readframes(current.getnframes())
                if pauses is not None:
                    current_frames = _trim_edge_silence(current_frames, channels, sample_width, frame_rate)
                frames.extend([silence, _soften_edges(current_frames, channels, sample_width, frame_rate)])

        with wave.open(str(output_path), "wb") as joined:
            joined.setnchannels(channels)
            joined.setsampwidth(sample_width)
            joined.setframerate(frame_rate)
            joined.writeframes(b"".join(frames))
    except (OSError, wave.Error) as exc:
        raise TtsError(f"TTS audio segments could not be joined: {exc}") from exc


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
        # Load the model once while keeping separate dialogue turns and their pauses.
        if not turns:
            raise TtsError("읽을 대사가 없습니다.")
        parts = [output_path.with_name(f"{output_path.stem}.part-{index}.wav") for index in range(len(turns))]
        payload = "\n".join(json.dumps({"text": _piper_text(text), "output_file": str(part)}, ensure_ascii=False) for (_, text), part in zip(turns, parts))
        try:
            _run_piper(command + ["--json-input"], payload, parts[0])
            _join_wav_files(parts, output_path)
        except TtsError:
            output_path.unlink(missing_ok=True)
            raise
        finally:
            for part in parts:
                part.unlink(missing_ok=True)
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
            _run_piper(command, _piper_text(text), part_path)
            parts.append(part_path)

        _join_wav_files(parts, output_path)
    except TtsError:
        output_path.unlink(missing_ok=True)
        raise
    finally:
        for part in parts:
            part.unlink(missing_ok=True)

    return f"/static/audio/{filename}"


_supertonic_lock = Lock()

_EXPRESSION_TAG = re.compile(r"<(laugh|breath|sigh|surprise|scream|throatclear|sad|angry|cough|yawn)>", re.I)


def _supertonic_spoken_text(text: str, expressions: bool = False) -> str:
    retained = False

    def expression(match):
        nonlocal retained
        tag = match.group(1).lower()
        if expressions and not retained and tag in {"laugh", "breath", "sigh"}:
            retained = True
            return f"<{tag}>"
        return " "

    return re.sub(r"\s+", " ", _EXPRESSION_TAG.sub(expression, text)).strip()


def _supertonic_delivery(text: str, tone: str, broadcast_format: str) -> dict:
    clean = _supertonic_spoken_text(text)
    base = {"casual": 1.0, "formal": .98, "cheerful": 1.05, "calm": .94}.get(tone, 1.0)
    kind, adjustment, chunk_pause = "explanation", -.02, .20
    if re.search(r"[?？][\"'”’]*$|(?:까요|나요|어때요|인가요)[.!]*$", clean):
        kind, adjustment, chunk_pause = "question", -.01, .18
    elif len(clean) <= 70 and re.match(r"(?:그랬군요|그럴 수 있|이해돼요|속상했|힘들었)", clean):
        kind, adjustment, chunk_pause = "empathy", -.04, .23
    elif len(clean) <= 45 and re.match(r"(?:아[,! .]|오[,! .]|와[,! .]|하하|맞아요|그러네요|그렇군요|좋아요|정말요|맞네요|그렇죠|Oh\b|Wow\b|Right\b)", clean, re.I):
        kind, adjustment, chunk_pause = "reaction", .02, .14
    elif re.match(r"(?:정리하면|마지막으로|오늘 기억|오늘은 여기까지|다음 시간)", clean):
        kind, adjustment, chunk_pause = "closing", -.03, .24
    if broadcast_format == "summary" and kind == "explanation":
        adjustment += .01
    return {"kind": kind, "speed": round(max(.88, min(1.10, base + adjustment)), 3),
            "silence_duration": chunk_pause}


def _supertonic_turn_pauses(turns: list[tuple[str, str]], deliveries: list[dict]) -> list[float]:
    pauses = []
    for index in range(1, len(turns)):
        previous, current = deliveries[index - 1]["kind"], deliveries[index]["kind"]
        if turns[index - 1][0] == turns[index][0]:
            gap = .28
        elif current == "reaction":
            gap = .10
        elif previous == "question":
            gap = .20
        elif current == "closing" or previous == "empathy":
            gap = .30
        else:
            gap = .22
        pauses.append(gap)
    return pauses


@lru_cache(maxsize=1)
def _supertonic_engine(model_dir: str):
    from supertonic import TTS
    return TTS(model="supertonic-3", model_dir=model_dir, auto_download=False,
               intra_op_num_threads=2, inter_op_num_threads=1)


def create_supertonic_speech_file(
    script: str,
    title: str = "broadcast",
    tone: str = "casual",
    broadcast_format: str = "deep_dive",
) -> str:
    turns = _speech_turns(script)
    if not turns:
        raise TtsError("읽을 대사가 없습니다.")
    names = list(dict.fromkeys(name for name, _ in turns if name))
    if len(names) > 2:
        raise TtsError("현재 라디오 TTS는 최대 두 명의 진행자만 지원합니다.")
    voice_a = os.environ.get("SUPERTONIC_VOICE_A", "F1").strip()
    voice_b = os.environ.get("SUPERTONIC_VOICE_B", "M1").strip()
    if not re.fullmatch(r"F[1-5]", voice_a) or not re.fullmatch(r"M[1-5]", voice_b):
        raise TtsError("Supertonic 여성 음성은 F1~F5, 남성 음성은 M1~M5로 설정해주세요.")
    # Keep named hosts stable even if the male host speaks first.
    mapping = {"민서": voice_a, "도윤": voice_b}
    remaining = [voice for voice in (voice_a, voice_b) if voice not in
                 {mapping[name] for name in names if name in mapping}]
    for name in names:
        if name not in mapping:
            mapping[name] = remaining.pop(0)
    model_dir = Path(os.environ.get("SUPERTONIC_MODEL_DIR", str(ROOT_DIR / ".tts-cache/supertonic3")))
    if not model_dir.is_absolute():
        model_dir = ROOT_DIR / model_dir
    filename, output = safe_audio_name(title, "wav")
    prosody = os.environ.get("SUPERTONIC_PROSODY", "1") == "1"
    expressions = os.environ.get("SUPERTONIC_EXPRESSIONS", "0") == "1"
    turns = [(name, _supertonic_spoken_text(text, expressions)) for name, text in turns]
    turns = [(name, text) for name, text in turns if text]
    if not turns:
        raise TtsError("읽을 대사가 없습니다.")
    deliveries = [_supertonic_delivery(text, tone, broadcast_format) for _, text in turns]
    base_speed = {"casual": 1.0, "formal": .98, "cheerful": 1.05, "calm": .94}.get(tone, 1.0)
    pauses = _supertonic_turn_pauses(turns, deliveries) if prosody else None
    try:
        # Serialize inference so concurrent requests cannot multiply CPU/model usage.
        with _supertonic_lock:
            engine = _supertonic_engine(str(model_dir.resolve()))
            styles = {voice: engine.get_voice_style(voice) for voice in {mapping.get(name, voice_a) for name, _ in turns}}
            with TemporaryDirectory(prefix="supertonic-", dir=STATIC_AUDIO_DIR) as directory:
                parts = []
                for index, (name, text) in enumerate(turns):
                    lang = "ko" if re.search(r"[가-힣]", text) else "en"
                    spoken = _piper_text(text) if lang == "ko" else text
                    audio, _ = engine.synthesize(spoken, voice_style=styles[mapping.get(name, voice_a)],
                                                 lang=lang, total_steps=8,
                                                 speed=deliveries[index]["speed"] if prosody else base_speed,
                                                 silence_duration=deliveries[index]["silence_duration"] if prosody else .18)
                    part = Path(directory) / f"{index}.wav"
                    engine.save_audio(audio, str(part))
                    with wave.open(str(part), "rb") as wav:
                        if wav.getnframes() == 0:
                            raise TtsError("Supertonic이 빈 음성을 생성했습니다.")
                    parts.append(part)
                _join_wav_files(parts, output, pauses=pauses)
    except Exception as exc:
        output.unlink(missing_ok=True)
        if isinstance(exc, TtsError):
            raise
        raise TtsError("Supertonic 음성 생성에 실패했습니다. 패키지와 로컬 모델 설치 상태를 확인해주세요.") from exc
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
    if provider == "supertonic":
        return create_supertonic_speech_file(script, title, tone, broadcast_format)
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
    if provider == "supertonic":
        return "Supertonic 3"
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
