"""Generate a reproducible before/after dialogue and opt-in expression-tag trial."""
import json
import os
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from backend.services.tts_service import create_speech_file, export_mp3, load_dotenv

SCRIPT = """민서: 산책하다가 길을 잘못 들어본 적 있나요?
도윤: 아, 저도 있어요. 지도를 봤는데도 반대쪽으로 걸었더라고요.
민서: 그랬군요. 약속 시간이 가까웠다면 꽤 걱정됐겠어요.
도윤: 맞아요. 그런데 잠깐 멈추고 주변 건물부터 확인하니까 방향을 다시 찾을 수 있었어요.
민서: 그러면 지도를 계속 들여다보기보다, 눈앞의 풍경과 비교해본 거네요?
도윤: 그렇죠. 급할수록 잠깐 멈추는 게 도움이 되더라고요.
민서: 오늘 기억할 건 하나예요. 길이 헷갈리면 안전한 곳에 멈춰서 다시 살펴보세요."""
TAG_SCRIPT = """민서: <laugh> 아, 저도 반대쪽으로 걸어간 적이 있어요.
도윤: <sigh> 한참 걸었는데 출발한 곳이 다시 보이더라고요."""

load_dotenv()
os.environ["TTS_PROVIDER"] = "supertonic"
report = []
for name, prosody, expressions, script in (
    ("prosody-before", "0", "0", SCRIPT),
    ("prosody-after", "1", "0", SCRIPT),
    ("prosody-tags-trial", "1", "1", TAG_SCRIPT),
):
    os.environ["SUPERTONIC_PROSODY"] = prosody
    os.environ["SUPERTONIC_EXPRESSIONS"] = expressions
    np.random.seed(42)
    start = time.perf_counter()
    url = create_speech_file(script, name)
    path = ROOT / "backend" / url.lstrip("/")
    with wave.open(str(path), "rb") as audio:
        seconds = audio.getnframes() / audio.getframerate()
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(np.float32)
        rms = float(np.sqrt(np.mean(samples ** 2)))
        if not seconds or rms < 1:
            raise RuntimeError(f"Empty or silent audio: {name}")
    mp3 = export_mp3(url)
    item = {"name": name, "seconds": round(seconds, 2), "elapsed": round(time.perf_counter() - start, 2),
            "rms": round(rms, 2), "mp3": "/static/audio/" + mp3.name}
    report.append(item)
    print(json.dumps(item), flush=True)
directory = ROOT / ".tts-cache/prosody-preview"
directory.mkdir(parents=True, exist_ok=True)
(directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
