import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.voice_clone_service import create_xtts_voice_test


if __name__ == "__main__":
    audio_url = create_xtts_voice_test(
        r"backend\reference_voices\user-sample.m4a",
        "안녕하세요. 지금은 제 목소리 샘플을 바탕으로 짧은 테스트 방송을 만들어보는 중입니다.",
        "xtts-user-sample",
    )
    print(audio_url)
