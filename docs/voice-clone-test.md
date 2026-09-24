# Voice Clone Test

ON-AIR can run a short local voice cloning test with Coqui XTTS.

This is intentionally separate from the main radio TTS flow because CPU-only generation can be slow.

## Flow

1. Upload your own voice sample.
2. Enter a short Korean test sentence.
3. Generate a short XTTS sample.
4. Listen before deciding whether to use it for full radio audio.

## Recommended Sample

- Use your own voice only.
- Record in a quiet room.
- Use 30-60 seconds if possible.
- Avoid music, effects, or background noise.
- WAV is preferred, but MP3 can also work.

## Install

Coqui XTTS is optional and not installed by default.

```bash
.venv\bin\python.exe -m pip install -r backend\requirements-xtts.txt
```

The first XTTS run downloads the model and can take a long time. CPU generation can also be slow.

## Settings

```txt
XTTS_MODEL=tts_models/multilingual/multi-dataset/xtts_v2
XTTS_DEVICE=cpu
```

Use only voices you own or have explicit consent to clone.
