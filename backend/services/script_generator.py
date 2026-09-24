import json
import os
from urllib.request import ProxyHandler, Request, build_opener

from dataclasses import dataclass
from typing import Literal


Tone = Literal["casual", "formal", "cheerful", "calm", "bright"]
BroadcastFormat = Literal["deep_dive", "summary", "critique", "debate"]
Language = Literal["ko", "en"]


@dataclass
class ScriptSegmentPlan:
    type: str
    title: str
    text: str


@dataclass
class ScriptPlan:
    concept: str
    format_label: str
    script: str
    segments: list[ScriptSegmentPlan]
    listener_comments: list[str]
    generation_provider: str = "offline"
    generation_notice: str = ""
    estimated_seconds: int = 0


class ScriptGenerationError(RuntimeError):
    """Raised when an explicitly requested local generator cannot respond."""


TONE_GUIDES = {
    "casual": {
        "label": "캐주얼",
        "host_a": "민서",
        "host_b": "도윤",
        "opening": "오늘은 너무 어렵게 말고, 편하게 들을 수 있게 풀어볼게요.",
        "ending": "오늘 방송은 여기까지입니다. 편하게 들어주셔서 고맙습니다.",
    },
    "formal": {
        "label": "포멀",
        "host_a": "서현",
        "host_b": "지훈",
        "opening": "핵심 개념과 실제 활용 사례를 차례로 정리해보겠습니다.",
        "ending": "이상으로 오늘의 방송을 마칩니다.",
    },
    "cheerful": {
        "label": "유쾌",
        "host_a": "하나",
        "host_b": "준",
        "opening": "조금 빠르고 산뜻하게, 듣다 보면 감이 잡히는 식으로 가보죠.",
        "ending": "남은 하루도 기분 좋은 흐름으로 이어가세요.",
    },
    "calm": {
        "label": "차분",
        "host_a": "유진",
        "host_b": "현우",
        "opening": "조금 천천히, 하나씩 짚어보겠습니다.",
        "ending": "잠시 숨을 고르듯 편안한 시간이었길 바랍니다.",
    },
    "bright": {
        "label": "밝음",
        "host_a": "라온",
        "host_b": "이안",
        "opening": "가볍지만 선명하게, 오늘의 포인트를 잡아보겠습니다.",
        "ending": "남은 시간도 산뜻하게 이어가세요.",
    },
}


FORMAT_LABELS = {
    "deep_dive": "심층 분석",
    "summary": "요약",
    "critique": "비평",
    "debate": "토론",
}


def analyze_topic(topic: str) -> dict[str, str]:
    lowered = topic.lower()

    if "인공지능" in topic or "ai" in lowered:
        return {
            "scene": "아침에 추천 영상을 보고, 점심엔 번역기를 쓰고, 저녁엔 챗봇에게 질문하는 하루",
            "simple": "사람이 하던 판단과 표현의 일부를 기계가 도와주는 기술",
            "example_a": "스마트폰 사진 보정, 음악 추천, 길 찾기처럼 이미 일상에 들어온 기능",
            "example_b": "글쓰기, 코딩, 고객 상담처럼 생산성을 바꾸는 도구",
            "tension": "편리함은 커지지만, 정보 신뢰도와 일자리 변화에 대한 걱정도 함께 커진다는 점",
            "takeaway": "인공지능은 멀리 있는 미래 기술이 아니라, 이미 생활 방식을 바꾸는 도구라는 점",
        }

    if "뉴스" in topic or "news" in lowered:
        return {
            "scene": "퇴근길 지하철에서 이어폰으로 듣는 짧은 브리핑",
            "simple": "오늘 하루의 중요한 흐름을 놓치지 않게 압축해주는 정보",
            "example_a": "정책, 경제, 생활 이슈 중 지금 알아두면 좋은 변화",
            "example_b": "내일 대화나 의사결정에 바로 도움이 되는 맥락",
            "tension": "소식이 너무 많아 중요한 것과 지나가는 이슈가 섞인다는 점",
            "takeaway": "많이 듣는 것보다 무엇을 기억할지 고르는 일이 중요하다는 점",
        }

    if "재즈" in topic or "카페" in topic or "jazz" in lowered:
        return {
            "scene": "조용한 카페 창가에 앉아 잔잔한 음악을 듣는 저녁",
            "simple": "공간의 분위기와 사람의 마음을 천천히 맞춰주는 음악",
            "example_a": "피아노와 베이스가 작게 흐르는 로파이 재즈",
            "example_b": "대화는 방해하지 않으면서도 공간을 따뜻하게 만드는 배경음",
            "tension": "감성적인 말만 반복하면 실제 정보가 약해질 수 있다는 점",
            "takeaway": "음악은 설명보다 먼저 분위기를 만들고, 이야기는 그 위에 얹힌다는 점",
        }

    if "데이트" in topic or "주말" in topic:
        return {
            "scene": "주말 약속을 앞두고 어디 갈지 고민하는 오후",
            "simple": "동선과 분위기, 선택지를 한 번에 정리해주는 추천",
            "example_a": "걷기 좋은 거리, 대화하기 좋은 카페, 부담 없는 식사 코스",
            "example_b": "날씨나 시간대에 따라 바꿀 수 있는 예비 선택지",
            "tension": "추천이 너무 많으면 오히려 결정하기 어려워진다는 점",
            "takeaway": "좋은 코스는 화려함보다 둘이 편하게 움직일 수 있는 흐름에서 나온다는 점",
        }

    if "도전" in topic or "프로젝트" in topic:
        return {
            "scene": "팀 프로젝트를 소개하는 발표 전날의 리허설",
            "simple": "아이디어의 필요성과 구현 과정을 설득력 있게 보여주는 작업",
            "example_a": "주제 입력에서 대본, 음성, 음악 추천으로 이어지는 제작 흐름",
            "example_b": "사용자가 직접 방송을 만드는 웹 기반 프로토타입",
            "tension": "기능 설명만 길어지면 서비스의 매력이 흐려질 수 있다는 점",
            "takeaway": "기술보다 사용자가 어떤 경험을 하게 되는지가 먼저 보여야 한다는 점",
        }

    return {
        "scene": "관심 있는 주제를 라디오처럼 편하게 풀어보는 시간",
        "simple": "복잡한 내용을 듣기 쉬운 순서로 바꾸는 이야기",
        "example_a": "처음 듣는 사람도 따라올 수 있는 쉬운 비유와 사례",
        "example_b": "중간중간 분위기를 바꾸는 음악과 짧은 코멘트",
        "tension": "주제가 넓어질수록 초점이 흐려질 수 있다는 점",
        "takeaway": "좋은 방송은 많은 내용을 넣는 것보다 듣는 길을 만들어주는 것이라는 점",
    }


def source_sentence(source: str) -> str:
    cleaned = source.strip()
    if not cleaned:
        return ""
    if cleaned.startswith(("http://", "https://")):
        return "참고 링크도 함께 들어왔지만, 오늘은 링크 자체보다 주제의 큰 흐름을 중심으로 이야기해보겠습니다."
    if len(cleaned) > 90:
        return f"참고 메모의 핵심은 '{cleaned[:90]}...' 이 부분으로 잡아보겠습니다."
    return f"참고 소스로는 '{cleaned}'가 들어와 있습니다."


def line(host: str, text: str) -> str:
    return f"{host}: {text}"


def block(title: str, *lines: str) -> str:
    return "\n".join([f"[{title}]", *lines])


def make_segments(broadcast_format: BroadcastFormat, topic: str, info: dict[str, str]) -> list[ScriptSegmentPlan]:
    if broadcast_format == "summary":
        return [
            ScriptSegmentPlan("opening", "오프닝", f"'{topic}'을 짧게 소개하고 오늘 기억할 핵심을 먼저 제시합니다."),
            ScriptSegmentPlan("main", "핵심 요약", f"{info['simple']}이라는 관점에서 주요 포인트를 세 가지로 압축합니다."),
            ScriptSegmentPlan("music", "음악 소개", "브리핑 흐름을 방해하지 않는 음악으로 분위기를 가볍게 전환합니다."),
            ScriptSegmentPlan("closing", "클로징", f"마지막에 {info['takeaway']}을 다시 짚고 마무리합니다."),
        ]
    if broadcast_format == "critique":
        return [
            ScriptSegmentPlan("opening", "오프닝", f"'{topic}'을 소개가 아니라 비평 관점으로 다룹니다."),
            ScriptSegmentPlan("strength", "좋은 점", f"{info['example_a']} 같은 강점을 먼저 짚습니다."),
            ScriptSegmentPlan("critique", "다듬을 점", f"{info['tension']}을 개선 포인트로 제시합니다."),
            ScriptSegmentPlan("closing", "클로징", "장점과 보완점을 균형 있게 정리합니다."),
        ]
    if broadcast_format == "debate":
        return [
            ScriptSegmentPlan("opening", "오프닝", f"'{topic}'을 두 진행자가 서로 다른 시선으로 꺼냅니다."),
            ScriptSegmentPlan("position_a", "관점 A", f"{info['example_a']}를 근거로 긍정적인 면을 제시합니다."),
            ScriptSegmentPlan("position_b", "관점 B", f"{info['tension']}을 근거로 신중한 시선을 제시합니다."),
            ScriptSegmentPlan("closing", "클로징", "양쪽 관점을 비교하며 청취자가 생각할 지점을 남깁니다."),
        ]
    return [
        ScriptSegmentPlan("opening", "오프닝", f"'{topic}'을 오늘의 생활 장면과 연결해 시작합니다."),
        ScriptSegmentPlan("context", "맥락 잡기", f"{info['simple']}이라는 큰 틀을 쉬운 예시로 풉니다."),
        ScriptSegmentPlan("connection", "연결 포인트", f"{info['example_a']}와 {info['example_b']}를 이어 설명합니다."),
        ScriptSegmentPlan("music", "음악 소개", "중간 음악을 방송 흐름의 전환점으로 사용합니다."),
        ScriptSegmentPlan("closing", "클로징", f"{info['takeaway']}을 남기며 마무리합니다."),
    ]


def make_deep_dive_script(topic: str, tone: Tone, duration: int, source: str, music: list[str]) -> str:
    guide = TONE_GUIDES[tone]
    info = analyze_topic(topic)
    host_a = guide["host_a"]
    host_b = guide["host_b"]
    track_a = music[0] if music else "Warm City Drive"
    track_b = music[1] if len(music) > 1 else track_a
    source_note = source_sentence(source)

    return "\n\n".join(
        [
            block(
                "00:00 오프닝",
                line(host_a, f"안녕하세요. On-AI-r입니다. 오늘은 '{topic}'을 주제로 {duration}분 정도 함께 이야기해볼게요."),
                line(host_b, guide["opening"]),
                line(host_a, f"장면을 하나 떠올려보면요. {info['scene']}. 오늘 방송은 바로 그 느낌에서 출발합니다."),
                line(host_b, source_note or "어렵게 정의부터 외우기보다, 우리가 실제로 어디서 마주치는지부터 보면 훨씬 편해집니다."),
            ),
            block(
                "01:00 첫 번째 이야기",
                line(host_a, f"먼저 아주 쉽게 말하면, {topic}은 {info['simple']}이라고 볼 수 있습니다."),
                line(host_b, f"예를 들면 {info['example_a']} 같은 게 있죠. 사실 특별한 순간에만 만나는 게 아니라 이미 꽤 가까이 와 있습니다."),
                line(host_a, "맞아요. 그래서 이 주제를 이야기할 때는 기술 자체보다, 이게 우리의 하루를 어떻게 바꾸는지를 같이 봐야 합니다."),
            ),
            block(
                "02:10 조금 더 깊게",
                line(host_b, f"한 단계 더 들어가면 {info['example_b']}도 중요합니다."),
                line(host_a, "여기서 흥미로운 건, 같은 기술이라도 누가 어떻게 쓰느냐에 따라 느낌이 완전히 달라진다는 점이에요."),
                line(host_b, f"그렇죠. 다만 {info['tension']}도 놓치면 안 됩니다. 편리하다고 해서 무조건 좋은 쪽으로만 흘러가진 않으니까요."),
                line(host_a, "그래서 오늘의 핵심은 찬성이나 반대 하나로 끝내는 게 아니라, 잘 쓰기 위한 감각을 잡는 데 있습니다."),
            ),
            block(
                "03:20 음악 전환",
                line(host_a, f"여기서 잠깐 분위기를 바꿔볼게요. 첫 번째 추천 트랙은 '{track_a}'입니다."),
                line(host_b, "말이 조금 깊어졌을 때는 음악이 한 번 숨을 만들어주는 게 좋습니다. 너무 무겁지 않게 다음 이야기로 넘어갈 수 있거든요."),
                line(host_a, f"클로징 전에는 '{track_b}'를 깔면 오늘 이야기의 여운을 정리하기 좋겠습니다."),
            ),
            block(
                "04:10 청취자 코멘트",
                line(host_b, f"방금 들어온 청취자 코멘트도 하나 소개해볼게요. '{topic}'을 막연하게만 생각했는데, 생활 속 예시로 들으니 훨씬 가깝게 느껴진다는 의견입니다."),
                line(host_a, "좋은 포인트예요. 결국 좋은 방송은 어려운 걸 어렵게 말하는 게 아니라, 내가 이미 알고 있는 장면과 연결해주는 거니까요."),
            ),
            block(
                "04:45 클로징",
                line(host_a, f"오늘 정리하면, {info['takeaway']}입니다."),
                line(host_b, "그리고 중요한 건 너무 멀리 있는 이야기로만 보지 않는 거예요. 내 생활 안에서 어떻게 쓰이고 있는지 보는 순간 훨씬 선명해집니다."),
                line(host_a, f"{guide['ending']} 지금까지 On-AI-r이었습니다."),
            ),
        ]
    )


def make_summary_script(topic: str, tone: Tone, duration: int, source: str, music: list[str]) -> str:
    guide = TONE_GUIDES[tone]
    info = analyze_topic(topic)
    host = guide["host_a"]
    track = music[0] if music else "Soft Newsroom Pulse"
    source_note = source_sentence(source)

    return "\n\n".join(
        [
            block(
                "00:00 오프닝",
                line(host, f"안녕하세요. On-AI-r입니다. 오늘은 '{topic}'을 빠르게 정리해드릴게요."),
                line(host, source_note or "긴 설명보다 핵심만 먼저 잡아보겠습니다."),
            ),
            block(
                "00:40 핵심 요약",
                line(host, f"첫째, {topic}은 {info['simple']}입니다."),
                line(host, f"둘째, 대표적인 장면은 {info['example_a']}입니다."),
                line(host, f"셋째, 기억할 점은 {info['takeaway']}입니다."),
            ),
            block(
                "02:00 주의할 점",
                line(host, f"다만 {info['tension']}은 꼭 생각해야 합니다. 이 부분을 놓치면 이야기가 한쪽으로만 흐를 수 있어요."),
            ),
            block(
                "03:10 음악 소개",
                line(host, f"오늘의 브리핑 배경으로는 '{track}'을 추천합니다. 정보 전달을 방해하지 않으면서 속도감을 살려주는 트랙입니다."),
            ),
            block(
                "04:30 클로징",
                line(host, f"오늘의 요약은 여기까지입니다. '{topic}'은 결국 우리의 선택과 사용 방식에 따라 의미가 달라집니다. {guide['ending']}"),
            ),
        ]
    )


def make_critique_script(topic: str, tone: Tone, source: str, music: list[str]) -> str:
    guide = TONE_GUIDES[tone]
    info = analyze_topic(topic)
    host = guide["host_a"]
    track = music[0] if music else "Quiet City Lights"
    source_note = source_sentence(source)

    return "\n\n".join(
        [
            block(
                "00:00 오프닝",
                line(host, f"오늘은 '{topic}'을 비평 형식으로 살펴보겠습니다."),
                line(host, source_note or "좋은 점과 아쉬운 점을 나눠서 보면 훨씬 선명해집니다."),
            ),
            block(
                "01:00 좋은 점",
                line(host, f"먼저 장점은 분명합니다. {info['example_a']}처럼 청취자가 바로 떠올릴 수 있는 장면이 있습니다."),
                line(host, f"또 {info['example_b']}까지 연결하면 방송의 폭도 꽤 넓어집니다."),
            ),
            block(
                "02:20 아쉬운 점",
                line(host, f"하지만 {info['tension']}은 조심해야 합니다."),
                line(host, "그래서 대본에서는 근거 없는 기대감보다 실제 사용 장면과 한계를 같이 다뤄야 합니다."),
            ),
            block(
                "03:30 음악 소개",
                line(host, f"비평형 방송에는 '{track}'처럼 말 사이의 여백을 살리는 음악이 어울립니다. 지적보다 정리에 가까운 분위기를 만들어주니까요."),
            ),
            block(
                "04:40 클로징",
                line(host, f"결론적으로 '{topic}'은 매력적인 주제지만, 좋은 방송이 되려면 장점과 한계를 함께 보여줘야 합니다. {guide['ending']}"),
            ),
        ]
    )


def make_debate_script(topic: str, tone: Tone, source: str, music: list[str]) -> str:
    guide = TONE_GUIDES[tone]
    info = analyze_topic(topic)
    host_a = guide["host_a"]
    host_b = guide["host_b"]
    track = music[0] if music else "Split Screen Groove"
    source_note = source_sentence(source)

    return "\n\n".join(
        [
            block(
                "00:00 오프닝",
                line(host_a, f"오늘의 토론 주제는 '{topic}'입니다."),
                line(host_b, "바로 결론을 내리기보다, 좋은 점과 걱정되는 점을 나눠서 이야기해보죠."),
                line(host_a, source_note or "먼저 생활 속 장면에서 출발해보겠습니다."),
            ),
            block(
                "01:00 긍정적 관점",
                line(host_a, f"저는 긍정적으로 봅니다. {info['example_a']}처럼 이미 사람들이 체감할 수 있는 변화가 있거든요."),
                line(host_a, f"그리고 {info['example_b']}까지 생각하면 앞으로 활용 가능성도 큽니다."),
            ),
            block(
                "02:15 신중한 관점",
                line(host_b, "저도 가능성은 인정하지만, 마냥 낙관하기는 어렵다고 봅니다."),
                line(host_b, f"특히 {info['tension']}은 실제로 꽤 큰 문제입니다."),
                line(host_b, "기술이나 아이디어가 좋아 보여도, 쓰는 사람이 이해하지 못하면 오히려 혼란을 만들 수 있거든요."),
            ),
            block(
                "03:20 쟁점 정리",
                line(host_a, "결국 핵심은 무조건 좋다, 나쁘다가 아니네요."),
                line(host_b, "맞아요. 어떤 장면에서, 어떤 기준으로 쓰느냐가 더 중요합니다."),
                line(host_a, f"여기서 '{track}' 같은 트랙을 잠깐 넣으면 토론의 긴장감도 조금 풀리겠습니다."),
            ),
            block(
                "04:40 클로징",
                line(host_a, f"오늘은 '{topic}'을 두 방향에서 살펴봤습니다."),
                line(host_b, f"마지막으로 남길 말은 이겁니다. {info['takeaway']}"),
                line(host_a, f"{guide['ending']} 지금까지 On-AI-r이었습니다."),
            ),
        ]
    )


def make_script(
    topic: str,
    tone: Tone,
    broadcast_format: BroadcastFormat,
    language: Language,
    source: str,
    duration_minutes: int,
    music_titles: list[str],
) -> str:
    if language == "en":
        return "English full-script generation will be enabled when a real LLM is connected."
    if broadcast_format == "summary":
        return make_summary_script(topic, tone, duration_minutes, source, music_titles)
    if broadcast_format == "critique":
        return make_critique_script(topic, tone, source, music_titles)
    if broadcast_format == "debate":
        return make_debate_script(topic, tone, source, music_titles)
    return make_deep_dive_script(topic, tone, duration_minutes, source, music_titles)


def generate_script_plan(
    topic: str,
    tone: Tone,
    broadcast_format: BroadcastFormat,
    language: Language,
    source: str,
    duration_minutes: int,
    music_titles: list[str],
) -> ScriptPlan:
    return _build_natural_plan(
        topic=topic,
        tone=tone,
        broadcast_format=broadcast_format,
        language=language,
        source=source,
        duration_minutes=duration_minutes,
    )


def _topic_particle(topic: str) -> str:
    """Pick a natural Korean object particle for a short topic label."""

    stripped = topic.rstrip()
    if not stripped:
        return "을"
    last = stripped[-1]
    if "가" <= last <= "힣":
        return "을" if (ord(last) - ord("가")) % 28 else "를"
    return "을"


def _japan_sections(topic: str) -> list[tuple[str, str, list[tuple[str, str]]]]:
    subject = f"'{topic}'"
    return [
        (
            "opening",
            "여행의 기준 세우기",
            [
                ("A", f"{subject}을 처음 준비한다면 유명한 장소부터 고르기보다 여행 기간과 이동량부터 정하는 게 좋아요."),
                ("B", "맞아요. 3박 4일이라면 도쿄와 교토를 한 번에 넣기보다 한 도시를 중심으로 잡아야 이동에 지치지 않죠."),
                ("A", "일주일 정도라면 두 도시를 연결할 수 있지만, 도시를 늘릴수록 관광지 수보다 이동 시간을 먼저 계산해야 합니다."),
            ],
        ),
        (
            "city",
            "도시별 여행 스타일",
            [
                ("B", "도쿄는 동네마다 분위기가 달라서 시부야, 아사쿠사, 긴자를 하루에 다 넣기보다 구역별로 묶는 편이 편해요."),
                ("A", "오사카는 난바를 중심으로 먹거리와 시내 일정을 잡기 좋고, 교토는 사찰 몇 곳을 고른 뒤 걷는 시간을 넉넉히 두는 게 핵심이고요."),
                ("B", "후쿠오카는 공항과 시내가 가까워 짧은 일정에 잘 맞습니다. 온천이나 근교를 넣고 싶다면 시내 관광을 조금 덜어내야 해요."),
            ],
        ),
        (
            "transport",
            "교통과 일정 사이",
            [
                ("A", "교통패스는 무조건 사는 것보다 실제 이동 경로를 먼저 적어본 다음 비교하는 게 맞습니다. 하루에 몇 번 타는지가 더 중요하거든요."),
                ("B", "공항에 도착한 날은 숙소에 짐을 맡기고 가까운 동네를 둘러보는 정도가 좋아요. 첫날부터 먼 곳을 넣으면 일정 전체가 밀릴 수 있어요."),
                ("A", "하루에 핵심 일정 하나와 가벼운 일정 하나만 두면 식당 대기나 길 찾기에 시간이 생겨도 여행이 무너지지 않습니다."),
            ],
        ),
        (
            "food",
            "먹거리와 예비 계획",
            [
                ("B", "식사는 꼭 먹고 싶은 한두 곳만 미리 정하고, 나머지는 그날 동선 안에서 고르는 방식이 부담이 적어요."),
                ("A", "예약이 필요한 곳과 줄이 긴 곳을 구분해두면 좋고요. 비가 오거나 컨디션이 떨어졌을 때 갈 실내 장소도 하나쯤 남겨두면 마음이 편합니다."),
                ("B", "결국 좋은 여행표는 빈칸이 없는 표가 아니라, 예상보다 늦어져도 다음 선택을 할 수 있는 표에 가깝습니다."),
            ],
        ),
        (
            "closing",
            "마무리",
            [
                ("A", f"정리하면 {subject}에서 가장 먼저 기억할 건 많이 보는 것보다 덜 지치면서 오래 기억할 장면을 고르는 일이에요."),
                ("B", "도시 하나를 제대로 걷고, 이동 사이에 쉬는 시간을 넣고, 날씨에 맞춰 바꿀 여지를 남기면 일정이 훨씬 자연스러워져요."),
            ],
        ),
    ]


def _known_sections(topic: str) -> list[tuple[str, str, list[tuple[str, str]]]] | None:
    value = topic.casefold()
    if any(word in value for word in ("일본", "도쿄", "오사카", "교토", "후쿠오카", "japan", "tokyo")) and any(
        word in value for word in ("여행", "관광", "trip", "travel")
    ):
        return _japan_sections(topic)

    subject = f"'{topic}'"
    if any(word in value for word in ("야구", "baseball")):
        details = [
            ("A", "야구를 처음 보면 선수들이 한 번에 움직이지 않아서 어디를 봐야 할지 헷갈릴 수 있어요."),
            ("B", "그럴 때는 투수와 타자만 보지 말고, 주자가 어느 베이스에 있는지도 같이 보면 흐름이 잡힙니다."),
            ("A", "지금 몇 아웃인지와 주자가 어디에 있는지만 따라가도 번트나 도루 같은 작전이 왜 나오는지 보이기 시작해요."),
        ]
        return [("opening", "경기의 흐름 잡기", details), ("rules", "아웃과 득점", [("B", "타자가 세 번 스트라이크를 받으면 아웃이고, 공을 쳐서 베이스를 돌아 홈으로 들어오면 득점이에요."), ("A", "공이 간 방향과 주자의 움직임을 함께 보면 수비가 무엇을 노리는지도 자연스럽게 보입니다.")]), ("closing", "마무리", [("A", "야구는 모든 규칙을 외워야 재미있는 게 아니라, 지금 주자가 어디에 있고 몇 아웃인지부터 따라가면 충분합니다."), ("B", "한 이닝의 흐름만 따라가도 경기 보는 재미가 달라질 거예요.")])]

    if any(word in value for word in ("요리", "레시피", "쿠킹", "cooking")):
        return [("opening", "준비가 절반", [("A", f"{subject}을 시작할 때 재료를 전부 꺼내고 썰어두면 중간에 불을 켠 채로 허둥대는 일이 줄어요."), ("B", "익는 시간이 다른 재료는 먼저 넣을 것과 나중에 넣을 것을 나눠두는 게 핵심이죠.")]), ("method", "불과 간 조절", [("B", "센 불이 항상 빠른 건 아니에요. 겉만 타고 속이 익지 않을 수 있어서 볶은 뒤에는 중불로 낮추는 경우가 많습니다."), ("A", "간은 한꺼번에 바꾸지 말고 조금씩 더하면서 마지막에 맛을 보는 게 안전해요.")]), ("closing", "마무리", [("A", "맛있는 요리는 복잡한 재료보다 순서를 지키고 중간중간 맛을 확인하는 데서 시작됩니다."), ("B", "다음번에 바꿀 점 하나만 기록해도 금방 내 레시피가 생겨요.")])]

    if any(word in value for word in ("재즈", "jazz")):
        return [("opening", "처음 듣는 법", [("A", f"{subject}이 어렵게 느껴진다면 장르 이름보다 어떤 악기가 먼저 들리는지부터 따라가 보세요."), ("B", "피아노가 리듬을 만들고 베이스가 바닥을 잡는지 들으면 훨씬 가까워집니다.")]), ("listen", "즉흥연주", [("B", "재즈의 즉흥연주는 아무렇게나 연주한다는 뜻이 아니라, 기본 멜로디 위에서 대화를 이어가는 방식에 가까워요."), ("A", "그래서 같은 곡도 연주자와 순간에 따라 분위기가 달라질 수 있습니다.")]), ("closing", "마무리", [("A", "재즈는 정답을 맞히는 음악이 아니라 악기 사이의 간격과 변화를 듣는 음악이라고 생각하면 편합니다."), ("B", "한 곡을 여러 번 들으며 다르게 들리는 부분을 찾는 것만으로도 충분히 좋은 감상이 돼요.")])]

    if any(word in value for word in ("인공지능", "머신러닝", "machine learning")) or value.strip() in {"ai", "a.i."}:
        return [("opening", "가까운 장면", [("A", f"{subject}은 거창한 연구실 이야기만은 아니에요. 사진 보정, 번역, 추천처럼 이미 매일 쓰는 기능 안에 들어와 있습니다."), ("B", "중요한 건 무엇이든 대신하게 하는 게 아니라, 사람이 초안을 만들거나 선택지를 비교할 때 보조로 쓰는 거죠.")]), ("use", "잘 맞는 일과 확인할 일", [("B", "반복되는 초안 작성이나 자료 정리는 도움을 받기 좋아요."), ("A", "다만 결과가 그럴듯해도 사실이라는 보장은 없어서 날짜, 숫자, 인용은 사람이 다시 확인해야 합니다.")]), ("closing", "마무리", [("B", "잘 쓰는 사람은 답을 그대로 믿는 사람이 아니라 맡길 일과 직접 확인할 일을 나누는 사람에 가깝습니다."), ("A", "작은 일부터 결과를 비교해보면 내 생활에 맞는 사용법을 찾을 수 있어요.")])]
    return None


def _generic_sections(topic: str) -> list[tuple[str, str, list[tuple[str, str]]]]:
    subject = f"'{topic}'"
    particle = _topic_particle(topic)
    return [
        ("opening", "주제 열기", [("A", f"오늘은 {subject}{particle} 사전식 정의보다, 실제로 언제 만나고 왜 궁금해지는지부터 이야기해볼게요."), ("B", f"좋아요. 처음 듣는 사람이라면 {subject}{particle} 한 문장으로 설명하기보다 익숙한 장면에 연결하는 편이 이해하기 쉽겠죠.")]),
        ("context", "맥락 잡기", [("B", f"먼저 {subject}{particle} 알아볼 때 가장 먼저 확인할 건 목적과 기준이에요. 무엇을 하려는지에 따라 중요한 정보가 달라지거든요."), ("A", f"그래서 {subject}{particle} 무조건 좋다거나 어렵다고 단정하기보다, 내 상황에서 어떤 선택지가 있는지 나눠보는 게 좋겠습니다.")]),
        ("practical", "직접 살펴보기", [("A", f"실제로 {subject}{particle} 접한다면 작은 사례 하나부터 비교해보세요. 기대한 점과 달랐던 점을 적어두면 다음 판단이 훨씬 쉬워집니다."), ("B", "그리고 출처가 필요한 정보와 사람마다 달라지는 경험을 구분하면 과장된 결론을 피할 수 있어요.")]),
        ("closing", "마무리", [("B", f"결국 {subject}{particle} 잘 이해하는 방법은 한 번에 결론을 내리는 게 아니라, 내 목적에 맞는 질문을 하나씩 좁혀가는 데 있습니다."), ("A", "오늘 이야기에서 바로 적용할 수 있는 기준 하나를 골라 작게 시험해보면 좋겠습니다.")]),
    ]


def _ollama_sections(
    topic: str,
    broadcast_format: BroadcastFormat,
    language: Language,
    duration_minutes: int,
) -> list[tuple[str, str, list[tuple[str, str]]]] | None:
    if language != "ko" or os.getenv("SCRIPT_PROVIDER", "auto").lower() == "offline":
        return None

    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    if not base_url.startswith(("http://127.0.0.1:", "http://localhost:")):
        return None
    opener = build_opener(ProxyHandler({}))
    try:
        opener.open(f"{base_url}/api/tags", timeout=1).read(4096)
        prompt = f"""한국어 라디오 대본을 작성하세요.
주제: {topic}
형식: {FORMAT_LABELS[broadcast_format]}
반드시 주제에 구체적으로 답하고, 주제와 무관한 기술/방송 제작 문장을 넣지 마세요.
최소 4개 섹션, 각 섹션에 진행자 A/B의 자연스러운 대화 2~4줄을 작성하세요.
현재 사실이나 가격을 추측하지 말고, 근거가 필요한 내용은 확인 기준으로 말하세요.
JSON만 출력하세요. 형식: {{"sections":[{{"title":"섹션 제목","dialogue":[{{"speaker":"A","text":"대사"}},{{"speaker":"B","text":"대사"}}]}}]}}"""
        payload = json.dumps({
            "model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.65, "repeat_penalty": 1.12, "num_predict": 2200},
        }).encode("utf-8")
        request = Request(f"{base_url}/api/generate", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with opener.open(request, timeout=int(os.getenv("OLLAMA_TIMEOUT", "90"))) as response:
            raw = json.loads(response.read(2_000_000).decode("utf-8"))
        draft = json.loads(raw.get("response", "{}"))
        sections = []
        for index, item in enumerate(draft.get("sections", [])):
            turns = []
            for turn in item.get("dialogue", []):
                speaker = "B" if turn.get("speaker") == "B" else "A"
                text = str(turn.get("text", "")).strip()
                if text:
                    turns.append((speaker, text))
            if turns:
                sections.append((f"local_{index}", str(item.get("title", f"이야기 {index + 1}"))[:80], turns[:8]))
        return sections if len(sections) >= 3 else None
    except Exception:
        return None


def _estimate_section_seconds(turns: list[tuple[str, str]]) -> int:
    section_text = "\n".join(text for _, text in turns)
    return max(24, min(150, len(section_text.replace(" ", "")) // 6))


def _duration_followup(
    topic: str,
    segment_type: str,
    round_index: int,
) -> list[tuple[str, str]]:
    subject = f"'{topic}'"
    focus_by_type = {
        "opening": "처음 방향을 정하는 기준",
        "city": "선택지마다 달라지는 분위기와 우선순위",
        "transport": "시간과 이동 부담을 줄이는 방법",
        "food": "예산과 취향을 함께 맞추는 방법",
        "closing": "실제로 적용하기 전에 점검할 항목",
    }
    focus = focus_by_type.get(segment_type, "실제 상황에서 선택하는 기준")
    if round_index % 3 == 0:
        return [
            ("A", f"그럼 {subject}를 실제로 준비하거나 선택할 때는 {focus}부터 짚어보면 좋겠네요. 처음부터 모든 경우의 수를 정하려고 하면 오히려 결정이 늦어질 수 있잖아요."),
            ("B", f"맞아요. 우선 {subject}에서 꼭 지키고 싶은 조건을 한두 가지로 줄인 다음, 나머지는 현장에서 바꿀 수 있게 여지를 남겨두는 편이 현실적입니다."),
            ("A", f"결국 {subject}는 정답을 외우는 것보다 내 상황에 맞는 기준을 세우는 게 중요하겠어요. 그 기준만 분명하면 예상과 다른 상황에서도 다음 선택을 이어갈 수 있으니까요."),
        ]
    if round_index % 3 == 1:
        return [
            ("A", f"한 가지 더 생각해 볼 점은 {subject}를 계획할 때 생기는 작은 변수예요. 시간이 부족하거나 예상보다 비용이 커졌을 때 무엇을 먼저 조정할지 정해두면 당황하지 않습니다."),
            ("B", "저라면 꼭 필요한 부분은 남기고, 순서를 바꾸거나 규모를 줄일 수 있는 부분부터 조정할 것 같아요. 그렇게 하면 계획 전체를 포기하지 않아도 됩니다."),
            ("A", f"네, {subject}를 오래 즐기려면 처음 계획을 지키는 것보다 상황에 맞게 고쳐 가는 태도가 더 중요하겠네요."),
        ]
    return [
        ("A", f"처음 접하는 청취자라면 {subject}에서 흔히 놓치는 부분도 궁금할 텐데요. 겉으로 보이는 장점만 보고 결정하면 어떤 아쉬움이 생길 수 있을까요?"),
        ("B", "대부분은 시간이나 준비 순서처럼 눈에 잘 안 보이는 비용을 빼먹기 쉬워요. 그래서 선택하기 전에 실제로 필요한 시간과 수고를 함께 적어보는 게 좋습니다."),
        ("A", f"그 과정을 거치면 {subject}를 막연한 기대가 아니라 내가 감당할 수 있는 계획으로 바꿀 수 있겠어요."),
    ]


def _extend_sections_to_duration(
    topic: str,
    duration_minutes: int,
    sections: list[tuple[str, str, list[tuple[str, str]]]],
) -> list[tuple[str, str, list[tuple[str, str]]]]:
    """Add topic-aware follow-ups until the script reaches its requested duration."""

    expanded = [(segment_type, title, list(turns)) for segment_type, title, turns in sections]
    if not expanded:
        return expanded

    target_seconds = max(60, duration_minutes * 60)
    estimated_seconds = sum(_estimate_section_seconds(turns) for _, _, turns in expanded)
    base_sections = list(expanded)
    round_index = 0
    max_extra_sections = max(12, target_seconds // 20 + 12)

    while estimated_seconds < target_seconds and round_index < max_extra_sections:
        source_type, source_title, _ = base_sections[round_index % len(base_sections)]
        followup_turns = _duration_followup(topic, source_type, round_index)
        insert_at = min(round_index + 1, len(expanded))
        expanded.insert(
            insert_at,
            (f"{source_type}_followup_{round_index}", f"{source_title} 이어서", followup_turns),
        )
        estimated_seconds += _estimate_section_seconds(followup_turns)
        round_index += 1

    return expanded


def _render_natural_plan(
    topic: str,
    tone: Tone,
    broadcast_format: BroadcastFormat,
    language: Language,
    source: str,
    duration_minutes: int,
    sections: list[tuple[str, str, list[tuple[str, str]]]],
    provider: str,
) -> ScriptPlan:
    guide = TONE_GUIDES[tone]
    rendered_segments = []
    blocks = []
    elapsed = 0
    for segment_type, title, turns in sections:
        rendered_lines = []
        for speaker, text in turns:
            host = guide["host_b"] if speaker == "B" and broadcast_format not in {"summary", "critique"} else guide["host_a"]
            rendered_lines.append(line(host, text))
        segment_text = "\n".join(rendered_lines)
        rendered_segments.append(ScriptSegmentPlan(segment_type, title, segment_text))
        timestamp = f"{elapsed // 60:02d}:{elapsed % 60:02d}"
        blocks.append(block(f"{timestamp} {title}", *rendered_lines))
        elapsed += _estimate_section_seconds(turns)

    notice = "주제별 오프라인 대본"
    if provider == "ollama":
        notice = "Ollama 로컬 모델로 생성"
    if source.strip():
        blocks.insert(1, block("참고 메모", line(guide["host_a"], f"참고 자료는 '{source.strip()}'입니다. 링크 내용은 자동으로 확인하지 않고, 입력된 메모만 대화의 방향을 잡는 데 사용했습니다.")))

    question_lines = [f"{question}" for question in _listener_questions(topic)]
    concept = f"{duration_minutes}분 방송을 목표로 {topic}의 실제 선택과 맥락을 대화로 풀어보는 {TONE_GUIDES[tone]['label']} 톤의 {FORMAT_LABELS[broadcast_format]} 라디오"
    if language == "en":
        concept = f"A {FORMAT_LABELS[broadcast_format]} radio conversation about {topic}."
    return ScriptPlan(
        concept=concept,
        format_label=FORMAT_LABELS[broadcast_format],
        script="\n\n".join(blocks),
        segments=rendered_segments,
        listener_comments=question_lines,
        generation_provider=provider,
        generation_notice=notice,
        estimated_seconds=elapsed,
    )


def _listener_questions(topic: str) -> list[str]:
    pack = _known_sections(topic)
    if "일본" in topic or "도쿄" in topic or "오사카" in topic or "교토" in topic:
        return ["도시를 여러 곳 넣을 때 이동 시간을 어떻게 계산하면 좋을까요?", "교통패스는 어떤 기준으로 비교해야 할까요?"]
    if pack:
        return [f"{topic}을 처음 접할 때 가장 먼저 확인할 기준은 무엇인가요?", f"{topic}을 실제 상황에 적용할 때 조심할 점은 무엇인가요?"]
    return [f"{topic}을 처음 알아볼 때 어떤 질문부터 시작하면 좋을까요?", f"{topic}에 대해 확인되지 않은 정보를 구분하려면 무엇을 봐야 할까요?"]


def _build_natural_plan(
    topic: str,
    tone: Tone,
    broadcast_format: BroadcastFormat,
    language: Language,
    source: str,
    duration_minutes: int,
) -> ScriptPlan:
    if language == "en":
        sections = _ollama_sections(topic, broadcast_format, language, duration_minutes) or _generic_sections(topic)
        sections = _extend_sections_to_duration(topic, duration_minutes, sections)
        return _render_natural_plan(topic, tone, broadcast_format, language, source, duration_minutes, sections, "offline")

    sections = _known_sections(topic)
    provider = "offline"
    if sections is None:
        sections = _ollama_sections(topic, broadcast_format, language, duration_minutes)
        if sections:
            provider = "ollama"
        else:
            sections = _generic_sections(topic)
    sections = _extend_sections_to_duration(topic, duration_minutes, sections)
    return _render_natural_plan(topic, tone, broadcast_format, language, source, duration_minutes, sections, provider)
