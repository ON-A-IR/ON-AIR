# Local TTS

## Supertonic 3 (Current Default)

Install dependencies and download model files once:

```powershell
.\.venv-win\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv-win\Scripts\python.exe scripts/setup-supertonic.py
```

```txt
TTS_PROVIDER=supertonic
SUPERTONIC_MODEL_DIR=.tts-cache/supertonic3
SUPERTONIC_VOICE_A=F1
SUPERTONIC_VOICE_B=M1
SUPERTONIC_PROSODY=1
SUPERTONIC_EXPRESSIONS=0
```

Minseo uses female F1, Doyun uses male M1, even when Doyun speaks first.
Other host names use available voices in order of appearance. Single-host scripts
stay single-host. No training or reference recordings are required.
The CPU engine is loaded once per server process; inference is serialized.
Normal synthesis never downloads missing models or silently switches to Piper.
Restart the backend after changing `.env`. Existing broadcasts are not re-voiced.
Run `scripts/generate-samples.py` to update bundled previews with the same settings.

### Dialogue Delivery

`SUPERTONIC_PROSODY=1` uses deterministic sentence-shape rules, not an extra LLM call.
Questions, short reactions, empathy phrases, explanations, and closing lines receive
small speed/chunk-pause adjustments while retaining the selected overall tone.
Speaker changes use 0.10-0.30 second gaps; existing quiet WAV edges are shortened
with an 80 ms safety margin before fades, without removing internal pauses.
This is pacing control, not guaranteed semantic emotion or pitch control.

`SUPERTONIC_PROSODY=0` restores the previous per-tone speed and fixed 0.12 second
turn gaps. `SUPERTONIC_EXPRESSIONS=0` is the default: known expression tags are
removed before synthesis so they cannot accidentally be spoken as words.
Setting it to `1` retains at most one explicit `<laugh>`, `<sigh>`, or `<breath>`
per turn. No emotional sounds are automatically inserted. Audition tagged output
before using it; model behavior is not guaranteed. These are internal flags, not
new controls in the app.

```powershell
.\.venv-win\Scripts\python.exe scripts/preview-supertonic-prosody.py
```

The comparison script generates the same original dialogue with old/new pacing and
a separate opt-in tag trial. It checks nonempty audio and writes MP3 paths/timing
to `.tts-cache/prosody-preview/report.json`. This does not score listening quality.

Model: [Supertonic 3](https://huggingface.co/Supertone/supertonic-3).
Code uses MIT; weights use [OpenRAIL-M](https://huggingface.co/Supertone/supertonic-3/blob/main/LICENSE).
Public hosting requires license notices and enforceable usage restrictions, including
AI-generated disclosure and restrictions on nonconsensual impersonation.
This integration is local only and does not implement a public deployment or abuse controls.
The upstream repository is archived; ongoing maintenance is not guaranteed.

## Other Providers

ON-AIR also supports these TTS paths:

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

## Two-host radio

ON-AIR routes the first two named hosts in the script to two Piper speakers and removes host names before synthesis. To use this mode, `PIPER_MODEL` must point to a multi-speaker model whose `.onnx.json` contains `"num_speakers": 2` or more.

```txt
PIPER_SPEAKER_A=0
PIPER_SPEAKER_B=1
```

The current `ko_KR-kss-medium.onnx` model has one speaker. It can continue to generate a single voice, but it cannot produce two different voices. Replace it with a multi-speaker Korean Piper model before using the two-host mode.

## Provider Behavior

```txt
TTS_PROVIDER=auto
```

Auto mode tries Piper first when `PIPER_EXE` and `PIPER_MODEL` are set. If Piper is not configured, it falls back to ElevenLabs when an API key exists, then Windows SAPI.

```txt
TTS_PROVIDER=piper
```

Piper mode forces Piper. If the executable or model path is wrong, the `/api/tts` request fails instead of falling back.
