"""Generate bundled, original radio previews with the configured TTS provider."""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.services.tts_service import create_speech_file, export_mp3, load_dotenv

load_dotenv()
directory = ROOT / "public" / "samples"
manifest_path = directory / "voice-manifest.json"
try:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        manifest = {}
except (OSError, ValueError):
    manifest = {}

# Ignore unrelated settings and never write credentials into the public manifest.
settings = {key: value for key, value in os.environ.items()
            if key.startswith(("PIPER_", "SUPERTONIC_")) or key in {"TTS_PROVIDER", "ELEVENLABS_VOICE_ID"}}
assets = {}
for key in ("PIPER_MODEL", "PIPER_CONFIG", "PIPER_EXE"):
    path = Path(settings.get(key, ""))
    if path.is_file():
        stat = path.stat()
        assets[key] = [str(path.resolve()), stat.st_size, stat.st_mtime_ns]
        if key == "PIPER_CONFIG":
            assets[key].append(hashlib.sha256(path.read_bytes()).hexdigest())
engine = hashlib.sha256((ROOT / "backend/services/tts_service.py").read_bytes()).hexdigest()
if settings.get("TTS_PROVIDER") == "supertonic":
    model_dir = Path(settings.get("SUPERTONIC_MODEL_DIR", ".tts-cache/supertonic3"))
    if not model_dir.is_absolute():
        model_dir = ROOT / model_dir
    assets["supertonic"] = [(str(path.relative_to(model_dir)), path.stat().st_size, path.stat().st_mtime_ns)
                            for path in sorted(model_dir.rglob("*")) if path.is_file() and path.suffix in {".onnx", ".json"}]
force = "--force" in sys.argv
formats = {"이야기 라디오": "deep_dive", "한눈에 브리핑": "summary", "생각의 주파수": "critique", "두 가지 시선": "debate"}
for sample in json.loads((directory / "scripts.json").read_text(encoding="utf-8")):
    target = directory / f"{sample['id']}.mp3"
    fingerprint = hashlib.sha256(json.dumps([engine, settings, assets, sample], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if not force and target.exists() and target.stat().st_size and manifest.get(sample["id"]) == fingerprint:
        continue
    url = create_speech_file(sample["script"], sample["id"], "casual", formats[sample["format"]])
    temporary = target.with_suffix(".tmp.mp3")
    shutil.copy2(export_mp3(url), temporary)
    temporary.replace(target)
    manifest[sample["id"]] = fingerprint
    temporary_manifest = manifest_path.with_suffix(".tmp.json")
    temporary_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    temporary_manifest.replace(manifest_path)
    print(f"Created {target.name}", flush=True)
print("Radio samples are up to date.", flush=True)
