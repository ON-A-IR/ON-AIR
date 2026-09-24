# Local TTS

ON-AIR supports three TTS paths:

1. Piper local TTS
2. ElevenLabs, if an API key is configured
3. Windows SAPI fallback

For a free local TTS upgrade, use Piper.

## Piper Setup

1. Download Piper for Windows from the Piper releases page.
2. Download the Korean voice model:
   - `ko_KR-kss-medium.onnx`
   - `ko_KR-kss-medium.onnx.json`
3. Put the files somewhere local, for example:

```txt
C:\ONAIR\piper\piper.exe
C:\ONAIR\piper\models\ko_KR-kss-medium.onnx
C:\ONAIR\piper\models\ko_KR-kss-medium.onnx.json
```

4. Create `.env` from `.env.example` and set:

```txt
TTS_PROVIDER=piper
PIPER_EXE=C:\ONAIR\piper\piper.exe
PIPER_MODEL=C:\ONAIR\piper\models\ko_KR-kss-medium.onnx
```

`PIPER_CONFIG` is optional. Piper normally finds `ko_KR-kss-medium.onnx.json` automatically when it is next to the model file.

## Provider Behavior

```txt
TTS_PROVIDER=auto
```

Auto mode tries Piper first when `PIPER_EXE` and `PIPER_MODEL` are set. If Piper is not configured, it falls back to ElevenLabs when an API key exists, then Windows SAPI.

```txt
TTS_PROVIDER=piper
```

Piper mode forces Piper. If the executable or model path is wrong, the `/api/tts` request fails instead of falling back.
