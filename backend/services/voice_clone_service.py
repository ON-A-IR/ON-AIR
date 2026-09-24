import base64
import os
import re
import subprocess
import uuid
from pathlib import Path

from backend.services.tts_service import TtsError, safe_audio_name


ROOT_DIR = Path(__file__).resolve().parents[2]
REFERENCE_VOICE_DIR = ROOT_DIR / "backend" / "reference_voices"
TTS_CACHE_DIR = ROOT_DIR / ".tts-cache"
DEFAULT_XTTS_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
_XTTS_MODEL = None


def allow_xtts_checkpoint_loading() -> None:
    import torch

    if not hasattr(torch.serialization, "add_safe_globals"):
        return

    from TTS.config.shared_configs import BaseDatasetConfig
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import XttsArgs, XttsAudioConfig

    torch.serialization.add_safe_globals([XttsConfig, XttsArgs, XttsAudioConfig, BaseDatasetConfig])


def _safe_extension(file_name: str, mime_type: str) -> str:
    suffix = Path(file_name).suffix.lower().lstrip(".")
    if suffix in {"wav", "mp3", "m4a", "ogg", "flac"}:
        return suffix
    if "wav" in mime_type:
        return "wav"
    if "mpeg" in mime_type or "mp3" in mime_type:
        return "mp3"
    if "ogg" in mime_type:
        return "ogg"
    return "wav"


def save_reference_voice(file_name: str, audio_base64: str, mime_type: str = "") -> str:
    REFERENCE_VOICE_DIR.mkdir(parents=True, exist_ok=True)
    extension = _safe_extension(file_name, mime_type)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(file_name).stem).strip("-")[:32] or "voice"
    output_path = REFERENCE_VOICE_DIR / f"{safe_name}-{uuid.uuid4().hex[:10]}.{extension}"

    if "," in audio_base64:
        audio_base64 = audio_base64.split(",", 1)[1]

    try:
        audio_bytes = base64.b64decode(audio_base64, validate=True)
    except ValueError as exc:
        raise TtsError("목소리 샘플 파일을 읽지 못했습니다.") from exc

    if len(audio_bytes) < 1024:
        raise TtsError("목소리 샘플이 너무 짧거나 비어 있습니다.")

    output_path.write_bytes(audio_bytes)
    return str(output_path)


def prepare_reference_voice(reference_voice_path: str) -> str:
    source_path = Path(reference_voice_path)
    if source_path.suffix.lower() == ".wav":
        return str(source_path)

    wav_path = source_path.with_suffix(".wav")
    if wav_path.exists() and wav_path.stat().st_mtime >= source_path.stat().st_mtime:
        return str(wav_path)

    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise TtsError("m4a 샘플을 wav로 변환하려면 imageio-ffmpeg 설치가 필요합니다.") from exc

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg_exe,
        "-y",
        "-i",
        str(source_path),
        "-ac",
        "1",
        "-ar",
        "24000",
        "-t",
        "45",
        str(wav_path),
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=180)
    except subprocess.CalledProcessError as exc:
        wav_path.unlink(missing_ok=True)
        raise TtsError(f"목소리 샘플 wav 변환에 실패했습니다: {exc.stderr or exc.stdout}") from exc

    if not wav_path.exists() or wav_path.stat().st_size <= 44:
        wav_path.unlink(missing_ok=True)
        raise TtsError("목소리 샘플 wav 변환 결과가 비어 있습니다.")

    return str(wav_path)


def get_xtts_model():
    global _XTTS_MODEL
    if _XTTS_MODEL is not None:
        return _XTTS_MODEL

    try:
        from TTS.api import TTS
    except ImportError as exc:
        raise TtsError("Coqui XTTS가 아직 설치되어 있지 않습니다. `pip install TTS` 설치가 필요합니다.") from exc

    allow_xtts_checkpoint_loading()
    os.environ.setdefault("TTS_HOME", str(TTS_CACHE_DIR))
    model_name = os.environ.get("XTTS_MODEL", DEFAULT_XTTS_MODEL)
    device = os.environ.get("XTTS_DEVICE", "cpu")
    _XTTS_MODEL = TTS(model_name, progress_bar=False).to(device)
    return _XTTS_MODEL


def create_xtts_voice_test(reference_voice_path: str, text: str, title: str = "voice-test") -> str:
    reference_path = Path(prepare_reference_voice(reference_voice_path))
    if not reference_path.exists():
        raise TtsError("저장된 목소리 샘플을 찾지 못했습니다.")

    clean_text = re.sub(r"\s+", " ", text).strip()
    if not clean_text:
        raise TtsError("테스트 문장이 비어 있습니다.")

    filename, output_path = safe_audio_name(title, "wav")
    model = get_xtts_model()

    try:
        model.tts_to_file(
            text=clean_text[:180],
            speaker_wav=str(reference_path),
            language="ko",
            file_path=str(output_path),
        )
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        raise TtsError(f"XTTS voice test failed: {exc}") from exc

    if not output_path.exists() or output_path.stat().st_size <= 44:
        output_path.unlink(missing_ok=True)
        raise TtsError("XTTS가 유효한 음성 파일을 만들지 못했습니다.")

    return f"/static/audio/{filename}"
