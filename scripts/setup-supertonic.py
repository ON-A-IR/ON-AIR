"""Download the pinned Supertonic 3 assets before starting the app."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.services.tts_service import load_dotenv

load_dotenv()
os.environ.setdefault("HF_HOME", str(ROOT / ".tts-cache/huggingface"))
from supertonic import TTS

directory = Path(os.environ.get("SUPERTONIC_MODEL_DIR", ".tts-cache/supertonic3"))
if not directory.is_absolute():
    directory = ROOT / directory
engine = TTS(model="supertonic-3", model_dir=directory, auto_download=True,
             intra_op_num_threads=2, inter_op_num_threads=1)
print(f"Supertonic 3 ready: {directory}")
print("Voices: " + ", ".join(engine.voice_style_names))
