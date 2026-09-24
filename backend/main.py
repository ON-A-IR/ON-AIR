from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.services.script_generator import generate_script_plan
from backend.services.tts_service import TtsError, create_speech_file, get_tts_provider_label
from backend.services.voice_clone_service import create_xtts_voice_test, save_reference_voice


Tone = Literal["casual", "formal", "cheerful", "calm", "bright"]
BroadcastFormat = Literal["deep_dive", "summary", "critique", "debate"]
Language = Literal["ko", "en"]


class GenerateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=120)
    tone: Tone = "casual"
    broadcast_format: BroadcastFormat = Field(default="deep_dive", alias="format")
    language: Language = "ko"
    source: str = Field(default="", max_length=500)
    duration_minutes: int = Field(default=5, alias="durationMinutes", ge=1, le=30)


class MusicItem(BaseModel):
    title: str
    artist: str
    mood: str
    bpm: int
    start: str


class CueItem(BaseModel):
    time: str
    type: str
    text: str


class ScriptSegment(BaseModel):
    type: str
    title: str
    text: str


class GenerateResponse(BaseModel):
    title: str
    topic: str
    concept: str
    formatLabel: str
    script: str
    segments: list[ScriptSegment]
    listenerComments: list[str]
    music: list[MusicItem]
    cuesheet: list[CueItem]
    audioUrl: str
    duration: str
    generationProvider: str = "offline"
    generationNotice: str = ""
    estimatedSeconds: int = 0


class TtsRequest(BaseModel):
    script: str = Field(min_length=1)
    title: str = "broadcast"


class TtsResponse(BaseModel):
    audioUrl: str
    provider: str


class VoiceTestRequest(BaseModel):
    fileName: str = Field(min_length=1, max_length=160)
    audioBase64: str = Field(min_length=1)
    mimeType: str = ""
    text: str = Field(default="안녕하세요. 온에어 목소리 테스트입니다. 짧은 문장으로 먼저 확인해볼게요.", min_length=1, max_length=220)


class VoiceTestResponse(BaseModel):
    audioUrl: str
    provider: str
    referenceVoicePath: str


app = FastAPI(title="On-AI-r API", version="0.5.0")
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def recommend_music(topic: str, tone: Tone, broadcast_format: BroadcastFormat) -> list[MusicItem]:
    lower_topic = topic.lower()

    if "뉴스" in topic or "news" in lower_topic or broadcast_format == "summary":
        return [
            MusicItem(title="Soft Newsroom Pulse", artist="ONAIR Lab", mood="ambient beat", bpm=92, start="00:12"),
            MusicItem(title="Clear Morning Brief", artist="ONAIR Lab", mood="light electronic", bpm=104, start="02:10"),
        ]

    if "재즈" in topic or "카페" in topic or "jazz" in lower_topic:
        return [
            MusicItem(title="Midnight Seoul Keys", artist="ONAIR Lab", mood="lo-fi jazz", bpm=78, start="00:15"),
            MusicItem(title="Cafe Window Trio", artist="ONAIR Lab", mood="warm jazz", bpm=84, start="02:28"),
        ]

    if broadcast_format == "debate":
        return [
            MusicItem(title="Split Screen Groove", artist="ONAIR Lab", mood="talk show funk", bpm=102, start="00:16"),
            MusicItem(title="Counterpoint Drive", artist="ONAIR Lab", mood="upbeat discussion", bpm=108, start="02:35"),
        ]

    if tone in {"calm", "formal"} or broadcast_format == "critique":
        return [
            MusicItem(title="Quiet City Lights", artist="ONAIR Lab", mood="soft ambient", bpm=82, start="00:16"),
            MusicItem(title="Afterglow Briefing", artist="ONAIR Lab", mood="warm downtempo", bpm=88, start="02:35"),
        ]

    return [
        MusicItem(title="Warm City Drive", artist="ONAIR Lab", mood="future pop", bpm=110, start="00:16"),
        MusicItem(title="Weekend River Walk", artist="ONAIR Lab", mood="city pop", bpm=96, start="02:35"),
    ]


def build_cuesheet(music: list[MusicItem]) -> list[CueItem]:
    return [
        CueItem(time="00:00", type="intro", text="오프닝 멘트 및 주제 소개"),
        CueItem(time="00:35", type="talk", text="핵심 맥락과 진행자 대화"),
        CueItem(time=music[0].start, type="music", text=f"{music[0].title} 소개 및 진입"),
        CueItem(time="03:20", type="comment", text="청취자 반응 또는 쟁점 정리"),
        CueItem(time="04:30", type="outro", text="요약 및 클로징"),
    ]


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/generate", response_model=GenerateResponse)
def generate_broadcast(payload: GenerateRequest) -> GenerateResponse:
    music = recommend_music(payload.topic, payload.tone, payload.broadcast_format)
    script_plan = generate_script_plan(
        topic=payload.topic,
        tone=payload.tone,
        broadcast_format=payload.broadcast_format,
        language=payload.language,
        source=payload.source,
        duration_minutes=payload.duration_minutes,
        music_titles=[item.title for item in music],
    )

    return GenerateResponse(
        title=f"{payload.topic} 방송",
        topic=payload.topic,
        concept=script_plan.concept,
        formatLabel=script_plan.format_label,
        script=script_plan.script,
        segments=[ScriptSegment(**segment.__dict__) for segment in script_plan.segments],
        listenerComments=script_plan.listener_comments,
        music=music,
        cuesheet=build_cuesheet(music),
        audioUrl="",
        duration=(
            f"약 {script_plan.estimated_seconds // 60}분"
            if script_plan.estimated_seconds % 60 == 0
            else f"약 {script_plan.estimated_seconds // 60}분 {script_plan.estimated_seconds % 60}초"
        ),
        generationProvider=script_plan.generation_provider,
        generationNotice=script_plan.generation_notice,
        estimatedSeconds=script_plan.estimated_seconds,
    )


@app.post("/api/tts", response_model=TtsResponse)
def generate_tts(payload: TtsRequest) -> TtsResponse:
    try:
        audio_url = create_speech_file(payload.script, payload.title)
    except TtsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return TtsResponse(audioUrl=audio_url, provider=get_tts_provider_label())


@app.post("/api/voice-test", response_model=VoiceTestResponse)
def generate_voice_test(payload: VoiceTestRequest) -> VoiceTestResponse:
    try:
        reference_voice_path = save_reference_voice(payload.fileName, payload.audioBase64, payload.mimeType)
        audio_url = create_xtts_voice_test(reference_voice_path, payload.text)
    except TtsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return VoiceTestResponse(
        audioUrl=audio_url,
        provider="Coqui XTTS",
        referenceVoicePath=reference_voice_path,
    )
