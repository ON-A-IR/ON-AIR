# Piper 학습 조사와 준비 상태

확인일: 2026-10-11

## 실제 진행 상태

데이터 후보의 출처와 라이선스, 공식 학습 절차, 로컬 실행 환경을 조사했습니다. 이후 공개 음성 한 문장을 내려받아 CPU에서 공식 Piper VITS 파형 생성부의 역전파/가중치 갱신을 3단계 실행했습니다. 전체 대본→음성 모델 학습, 학습 의존성 설치 및 새 모델 적용은 하지 않았습니다. 현재 앱은 기존 Piper KSS 모델을 사용합니다.

## CPU 부분 실험 결과

- 코드: 별도 작업 폴더 `C:\Users\sunha\Documents\Codex\2026-09-23\a\cpu_piper_probe.py`
- 공식 Piper 학습 소스를 별도 `piper-cpu-experiment` 폴더에 다운로드했습니다. 앱 가상환경 패키지는 변경하지 않았습니다.
- 데이터: CC BY 4.0 Zeroth-Korean의 Hugging Face 미러 `Bingsu/zeroth-korean`에서 train 첫 음성 1개만 다운로드했습니다. 출처/변형 내용은 실험 출력의 `ATTRIBUTION.md`에 기록했습니다.
- 범위: 랜덤 초기화한 VITS Generator(약 166만 파라미터), 고정 랜덤 잠재 입력, 파형 L1 복원 손실. CPU 4스레드, 배치 1, 약 0.372초 음성 조각으로 3단계 실행.
- 단계별 시간: 0.213초 / 0.090초 / 0.080초
- L1 손실: 0.04146 → 0.04068 → 0.04044
- 종료 시 프로세스 RSS: 약 305.5MB. 최대 메모리 사용량을 측정한 값은 아닙니다.
- 결과: 부분 모델의 CPU 역전파와 가중치 갱신은 동작했습니다. 음질 향상, 텍스트 학습, 두 화자 학습, 전체 Piper 학습의 속도를 검증한 것은 아닙니다. 고정 입력 과적합 실험의 손실 감소를 음질 향상으로 해석하지 마세요.
- WSL Ubuntu의 Python은 3.8.10으로, 받은 현재 Piper 코드의 Python >=3.9 요구 사항보다 낮습니다. gcc/cmake도 해당 확인에서 발견되지 않았습니다. 전체 공식 학습 절차를 위해 별도 환경 구축이 필요합니다.
- 새 배포용 체크포인트/ONNX를 만들지 않았으며 `.env`, 현재 모델과 샘플 음성은 이 실험으로 변경하지 않았습니다.

## 데이터 후보

| 후보 | 출처 및 조건 | 판단 |
| --- | --- | --- |
| KSS | 현재 모델 카드에 데이터 라이선스 CC BY-NC-SA 4.0 명시 | 기존 모델이 이미 사용한 데이터. 비상업 조건을 고려해야 하며 같은 데이터 재학습이 품질 향상을 보장하지 않음 |
| Zeroth-Korean | OpenSLR SLR40, CC BY 4.0, 학습 음성 51.6시간, 105명, 압축 파일 약 10GB | 사람 음성과 전사가 있는 후보. 음성 인식용이므로 TTS 학습 전 화자별 분리 및 녹음/전사 품질 검증 필요. 현재 선택한 학습 데이터나 검증 완료 데이터는 아님 |
| daje/korean-tts-training | 120문장, 약 60.5MB, 배포자가 CC BY 4.0 표기 | Gemini TTS로 합성한 데이터. 배포자 라이선스 표기만으로 원본 제공자의 학습용 재사용 조건을 확인했다고 볼 수 없어 학습에 사용하지 않음 |

데이터가 공개되었다는 것과 원하는 라디오 억양을 학습하기에 적합하다는 것은 다릅니다. 화자, 녹음 환경과 전사가 일관적인지 먼저 확인해야 합니다.

## 확인한 로컬 환경

- 프로젝트 Python의 PyTorch: `2.1.2+cpu`
- `torch.cuda.is_available()`: `False`
- CUDA 장치: 0개
- 프로젝트 Python에 Piper 학습 패키지 없음
- `C:\ONAIR`에서 학습용 `.ckpt` 파일을 찾지 못함
- WSL 목록: Ubuntu-20.04, docker-desktop. Linux 내부의 학습 의존성은 미확인
- C 드라이브 여유 공간: 조사 시 약 480GB

현재 `.onnx`는 음성 생성에 사용하는 추론 파일입니다. 공식 미세조정 절차에 필요한 `.ckpt`와 다릅니다. CPU에서 학습을 원천적으로 할 수 없는 것은 아니지만, 현재 환경에서 유의미한 품질의 학습을 짧은 시간에 끝낸다고 약속할 수 없습니다.

## 공식 학습 절차와 다음 조건

공식 Piper 문서는 학습용 의존성, 빌드 도구와 음성/대본 CSV를 준비하고 PyTorch Lightning으로 학습한 뒤 ONNX로 내보내는 절차를 안내합니다. 기존 medium 품질 체크포인트에서의 미세조정을 권장하며, 하드웨어 안내에는 GPU 사용 사례가 있습니다.

다음 단계는 아래 조건이 충족되어야 합니다.

1. 권한과 TTS 적합성을 확인한 화자별 데이터 선정
2. 별도 학습 환경과 사용 가능한 GPU 확보 또는 장시간 CPU 실험 여부 결정
3. 라이선스와 호환성을 확인한 학습용 체크포인트 확보
4. 작은 데이터로 전처리/학습/ONNX 내보내기 전체 절차 검증
5. 학습에 쓰지 않은 동일 문장을 기존 모델과 청취 비교
6. 실제 개선이 확인된 모델만 앱에 적용하고 샘플 음성 갱신

유료 GPU 서비스 가입이나 비용 발생 작업은 진행하지 않았습니다. 기존 모델과 앱 설정은 변경하지 않았습니다.

## 근거 링크

- [Piper 공식 학습 문서](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/TRAINING.md)
- [현재 KSS 모델 카드](https://huggingface.co/rhasspy/piper-voices/blob/main/ko/ko_KR/kss/medium/MODEL_CARD)
- [Zeroth-Korean 원본 배포처](https://www.openslr.org/40/)
- [합성 음성 후보 데이터 카드](https://huggingface.co/datasets/daje/korean-tts-training)
- [부분 실험에 사용한 Zeroth-Korean 미러](https://huggingface.co/datasets/Bingsu/zeroth-korean)
