# ON-AIR

ON-AIR는 주제만 입력하면 라디오 방송용 대본과 진행 자료를 만들어 주는 로컬 방송 제작 도구입니다. 프론트엔드는 React/Vite, 백엔드는 FastAPI로 구성되어 있으며, 기본 대본 생성은 외부 API 키 없이 동작합니다.

## 주요 기능

- 주제, 분위기, 방송 형식, 언어, 참고 자료를 바탕으로 대본 생성
- 1~30분 분량 선택 및 요청 시간에 맞춘 대본 구성
- 주제에 맞는 오프닝, 대화 흐름, 실제 사례와 실행 방법, 마무리 생성
- 방송 콘셉트, 구간별 대본, 청취자 댓글, 음악 추천, 큐시트 제공
- Piper 또는 Windows SAPI를 이용한 로컬 음성 합성
- 선택 기능으로 Coqui XTTS 음성 클론 테스트
- Ollama가 설치되어 있으면 선택적으로 로컬 모델을 대본 생성에 사용

## 기술 스택

- Frontend: React 19, Vite
- Backend: Python, FastAPI, Uvicorn
- Script generation: ON-AIR 오프라인 생성기, 선택적 Ollama
- TTS: Piper, Windows SAPI, 선택적 ElevenLabs
- Voice clone test: 선택적 Coqui XTTS

## 요구 사항

- Windows
- Node.js와 npm
- Python 3.10 이상 권장
- 저장소 루트에 준비된 `.venv-win` 또는 `.venv` 가상환경

## 실행 방법

### 1. 의존성 설치

프론트엔드 의존성을 설치합니다.

```powershell
npm install
```

백엔드 가상환경이 아직 없다면 생성하고 기본 의존성을 설치합니다.

```powershell
py -3 -m venv .venv-win
.venv-win\Scripts\python.exe -m pip install -r backend\requirements.txt
```

### 2. 프론트엔드와 백엔드 한 번에 실행

프로젝트 루트(`C:\ONAIR\ON-AIR`)에서 아래 명령 하나만 실행합니다.

```powershell
Set-Location C:\ONAIR\ON-AIR
npm.cmd run start
```

실행 스크립트가 백엔드와 프론트엔드를 자동으로 시작합니다. 이미 실행 중인 서버가 있으면 중복으로 실행하지 않습니다.

접속 주소:

```txt
http://127.0.0.1:5173/
```

백엔드 상태 확인:

```txt
http://127.0.0.1:8000/api/health
```

정상 응답:

```json
{"status":"ok"}
```

### 3. 개별 실행이 필요한 경우

프론트엔드만 실행:

```powershell
npm.cmd run dev:frontend
```

백엔드만 실행:

```powershell
.venv-win\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## 환경 설정

`.env.example`을 복사해 `.env`를 만들 수 있습니다.

```powershell
Copy-Item .env.example .env
```

대본 생성은 API 키 없이 사용할 수 있습니다. TTS와 XTTS 설정은 아래 문서를 참고하세요.

- [로컬 TTS 설정](docs/local-tts.md)
- [XTTS 음성 클론 테스트](docs/voice-clone-test.md)

## 무료 로컬 TTS

Piper 실행 파일과 한국어 모델을 준비한 뒤 `.env`에 경로를 설정하면 외부 API 없이 음성을 만들 수 있습니다.

```txt
TTS_PROVIDER=piper
PIPER_EXE=C:\ONAIR\piper\piper.exe
PIPER_MODEL=C:\ONAIR\piper\models\ko_KR-kss-medium.onnx
```

자세한 내용은 [docs/local-tts.md](docs/local-tts.md)를 확인하세요.

라디오 대본은 두 진행자의 이름을 포함하지만, TTS로 변환할 때 이름은 읽지 않습니다. 다중 화자 Piper 모델을 연결하면 첫 번째 진행자는 `PIPER_SPEAKER_A`, 두 번째 진행자는 `PIPER_SPEAKER_B`로 분리해 음성을 합칩니다. 현재 저장된 `ko_KR-kss-medium.onnx`는 단일 화자 모델이므로 두 목소리를 사용하려면 다중 화자 모델로 교체해야 합니다.

## 빌드

프론트엔드 배포 빌드를 확인하려면 다음 명령을 사용합니다.

```powershell
npm.cmd run build
```

## API 요약

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/api/health` | 백엔드 상태 확인 |
| `POST` | `/api/generate` | 방송 대본과 방송 자료 생성 |
| `POST` | `/api/tts` | 대본을 음성 파일로 변환 |
| `POST` | `/api/voice-test` | XTTS 음성 클론 테스트 |

## 프로젝트 구조

```txt
ON-AIR/
├─ backend/              # FastAPI 서버와 대본/TTS 서비스
├─ src/                  # React 화면
├─ scripts/start-dev.ps1 # 프론트엔드와 백엔드 통합 실행 스크립트
├─ docs/                 # TTS 및 음성 클론 안내
├─ package.json          # 프론트엔드 명령과 의존성
└─ .env.example          # 환경 변수 예시
```

## 참고

- 생성된 대본은 방송 초안이므로 실제 방송 전 사실관계와 인용 자료를 확인하세요.
- 음성 클론은 본인이 소유하거나 명시적인 사용 동의를 받은 목소리만 사용하세요.
