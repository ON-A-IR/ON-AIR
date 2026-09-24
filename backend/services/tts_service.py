import json
import os
import re
import subprocess
import uuid
from pathlib import Path
from urllib import error, request


ROOT_DIR = Path(__file__).resolve().parents[2]
STATIC_AUDIO_DIR = ROOT_DIR / "backend" / "static" / "audio"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"


class TtsError(RuntimeError):
    pass


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


def script_for_tts(script: str) -> str:
    text = re.sub(r"\[[^\]]+\]", ". ", script)
    text = re.sub(r"([가-힣A-Za-z0-9]+):", r"\1.", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


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


def create_piper_speech_file(script: str, title: str = "broadcast") -> str:
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
    command = [
        str(piper_path),
        "--model",
        str(model_path),
        "--output_file",
        str(output_path),
    ]

    piper_config = os.environ.get("PIPER_CONFIG", "").strip()
    if piper_config:
        config_path = Path(piper_config)
        if not config_path.exists():
            raise TtsError(f"Piper config was not found: {config_path}")
        command.extend(["--config", str(config_path)])

    piper_espeak_data = os.environ.get("PIPER_ESPEAK_DATA", "").strip()
    if piper_espeak_data:
        espeak_data_path = Path(piper_espeak_data)
        if not espeak_data_path.exists():
            raise TtsError(f"Piper eSpeak data directory was not found: {espeak_data_path}")
        command.extend(["--espeak_data", str(espeak_data_path)])

    piper_speaker = os.environ.get("PIPER_SPEAKER", "").strip()
    if piper_speaker:
        command.extend(["--speaker", piper_speaker])

    try:
        subprocess.run(
            command,
            input=script_for_tts(script),
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


def create_speech_file(script: str, title: str = "broadcast") -> str:
    load_dotenv()

    provider = os.environ.get("TTS_PROVIDER", "auto").strip().lower()
    if provider == "piper":
        return create_piper_speech_file(script, title)
    if provider == "elevenlabs":
        return create_elevenlabs_speech_file(script, title)
    if provider in {"sapi", "windows", "local"}:
        return create_sapi_speech_file(script, title)

    if os.environ.get("PIPER_EXE") and os.environ.get("PIPER_MODEL"):
        try:
            return create_piper_speech_file(script, title)
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
