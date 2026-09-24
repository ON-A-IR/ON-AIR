﻿import { useEffect, useRef, useState } from "react";

const topicChips = [
  "서울 주말 데이트 코스",
  "퇴근길 10분 뉴스",
  "카페에서 듣는 재즈",
];

const toneOptions = [
  { value: "casual", label: "캐주얼" },
  { value: "formal", label: "포멀" },
  { value: "cheerful", label: "유쾌" },
  { value: "calm", label: "차분" },
];

const formatOptions = [
  {
    value: "deep_dive",
    title: "심층 분석",
    description: "두 호스트가 생동감 있게 주고받는 대화 형식으로, 주제를 분석하고 여러 주제를 연결합니다.",
  },
  {
    value: "summary",
    title: "요약",
    description: "소스의 핵심 아이디어가 무엇인지 빠르게 파악할 수 있도록 간결하게 요약합니다.",
  },
  {
    value: "critique",
    title: "비평",
    description: "소스에 대한 전문가의 비평으로, 자료를 개선하는 데 도움이 되는 건설적인 의견을 제공합니다.",
  },
  {
    value: "debate",
    title: "토론",
    description: "두 호스트가 진행하는 사례 깊은 토론으로, 소스와 관련해 다양한 관점을 조명합니다.",
  },
];

const generationSteps = [
  { title: "기획", active: "구성 설계 중", done: "구성 완료" },
  { title: "대본", active: "대본 작성 중", done: "대본 완료" },
  { title: "음악", active: "음악 탐색 중", done: "추천 완료" },
  { title: "믹싱", active: "믹싱 준비 중", done: "완성" },
];

const recentBroadcasts = [
  {
    title: "AI가 고른 오늘의 테크 뉴스",
    meta: "4분 12초 · 정보형",
    className: "card-purple",
    icon: "AI",
  },
  {
    title: "한강 산책용 시티팝 믹스",
    meta: "6분 03초 · 음악형",
    className: "card-green",
    icon: "FM",
  },
  {
    title: "퇴근길 마음 정리 라디오",
    meta: "5분 40초 · 힐링형",
    className: "card-orange",
    icon: "ON",
  },
];

function wait(milliseconds) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

function Header() {
  return (
    <header className="topbar">
      <a className="brand" href="/" aria-label="On-AI-r 홈">
        On-AI-r
      </a>
      <nav className="nav-links" aria-label="주요 메뉴">
        <a href="#generate">Create</a>
        <a href="#recent">Library</a>
        <a href="#recent">Explore</a>
      </nav>
      <div className="nav-actions">
        <a href="#recent">Recent</a>
        <button type="button">Start</button>
      </div>
    </header>
  );
}

function FormatSelector({ broadcastFormat, onFormatChange }) {
  return (
    <section className="format-section" aria-label="방송 형식">
      <h2>형식</h2>
      <div className="format-grid">
        {formatOptions.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`format-card ${broadcastFormat === option.value ? "selected" : ""}`}
            onClick={() => onFormatChange(option.value)}
          >
            <span>{option.title}</span>
            <p>{option.description}</p>
          </button>
        ))}
      </div>
    </section>
  );
}

function ToneSelector({ tone, onToneChange }) {
  return (
    <div className="tone-selector" aria-label="방송 톤앤매너">
      {toneOptions.map((option) => (
        <button
          key={option.value}
          type="button"
          className={tone === option.value ? "selected" : ""}
          onClick={() => onToneChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function BroadcastControls({
  language,
  durationMinutes,
  source,
  onLanguageChange,
  onDurationChange,
  onSourceChange,
}) {
  return (
    <div className="control-row">
      <label>
        <span>언어 선택</span>
        <select value={language} onChange={(event) => onLanguageChange(event.target.value)}>
          <option value="ko">한국어</option>
          <option value="en">English</option>
        </select>
      </label>
      <label>
        <span>길이</span>
        <select
          value={durationMinutes}
          onChange={(event) => onDurationChange(Number(event.target.value))}
        >
          <option value={5}>5분</option>
          <option value={10}>10분</option>
          <option value={15}>15분</option>
        </select>
      </label>
      <label>
        <span>소스</span>
        <input
          value={source}
          onChange={(event) => onSourceChange(event.target.value)}
          placeholder="참고할 자료나 링크"
        />
      </label>
    </div>
  );
}

function PromptBox({
  topic,
  tone,
  broadcastFormat,
  language,
  durationMinutes,
  source,
  loading,
  onTopicChange,
  onToneChange,
  onFormatChange,
  onLanguageChange,
  onDurationChange,
  onSourceChange,
  onPickTopic,
  onGenerate,
}) {
  return (
    <form className="prompt-box" id="generate" onSubmit={onGenerate}>
      <label className="sr-only" htmlFor="topic">
        방송 주제
      </label>
      <textarea
        id="topic"
        value={topic}
        onChange={(event) => onTopicChange(event.target.value)}
        placeholder="어떤 방송을 만들까요? 예: 오늘의 서울 핫플과 어울리는 음악"
      />
      <FormatSelector broadcastFormat={broadcastFormat} onFormatChange={onFormatChange} />
      <BroadcastControls
        language={language}
        durationMinutes={durationMinutes}
        source={source}
        onLanguageChange={onLanguageChange}
        onDurationChange={onDurationChange}
        onSourceChange={onSourceChange}
      />
      <ToneSelector tone={tone} onToneChange={onToneChange} />
      <div className="prompt-footer">
        <div className="chips" aria-label="추천 주제">
          {topicChips.map((chip) => (
            <button key={chip} type="button" onClick={() => onPickTopic(chip)}>
              {chip}
            </button>
          ))}
        </div>
        <button className="make-button" type="submit" disabled={loading}>
          {loading ? "생성 중" : "방송 만들기"}
        </button>
      </div>
    </form>
  );
}

function GenerationSteps({ visible, activeStep, completed }) {
  return (
    <section className={`generation-panel ${visible ? "show" : ""}`} aria-label="생성 단계">
      {generationSteps.map((step, index) => {
        const isActive = activeStep === index && !completed;
        const isDone = completed || index < activeStep;
        const status = isDone ? step.done : isActive ? step.active : "대기 중";

        return (
          <article
            key={step.title}
            className={`step ${isActive ? "active" : ""} ${isDone ? "done" : ""}`}
          >
            <span>{String(index + 1).padStart(2, "0")}</span>
            <strong>{step.title}</strong>
            <small>{status}</small>
          </article>
        );
      })}
    </section>
  );
}

function ResultPanel({ result }) {
  const [playing, setPlaying] = useState(false);
  const [ttsLoading, setTtsLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState("");
  const [ttsProvider, setTtsProvider] = useState("");
  const [viewMode, setViewMode] = useState("segments");
  const utteranceRef = useRef(null);
  const audioRef = useRef(null);

  useEffect(() => {
    window.speechSynthesis?.cancel();
    audioRef.current?.pause();
    audioRef.current = null;
    setPlaying(false);
    setTtsLoading(false);
    setAudioUrl(result?.audioUrl || "");
    setTtsProvider("");
    setViewMode("segments");

    return () => {
      window.speechSynthesis?.cancel();
      audioRef.current?.pause();
    };
  }, [result]);

  if (!result) return null;

  function scriptForSpeech(script) {
    return script
      .replace(/\[[^\]]+\]/g, ". ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function handleSpeechToggle() {
    if (playing) {
      audioRef.current?.pause();
      window.speechSynthesis.cancel();
      setPlaying(false);
      return;
    }

    playGeneratedAudio();
  }

  function playBrowserTts() {
    if (!("speechSynthesis" in window)) {
      window.alert("이 브라우저는 테스트용 음성 읽기를 지원하지 않습니다.");
      return;
    }

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(scriptForSpeech(result.script));
    utterance.lang = "ko-KR";
    utterance.rate = 0.95;
    utterance.pitch = 1;
    utterance.volume = 1;
    utterance.onend = () => setPlaying(false);
    utterance.onerror = () => setPlaying(false);

    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
    setPlaying(true);
  }

  async function getAudioUrl() {
    if (audioUrl) return audioUrl;

    const response = await fetch("/api/tts", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        script: result.script,
        title: result.title,
      }),
    });

    if (!response.ok) {
      throw new Error("외부 TTS 생성에 실패했습니다.");
    }

    const data = await response.json();
    setAudioUrl(data.audioUrl);
    setTtsProvider(data.provider || "로컬 TTS");
    return data.audioUrl;
  }

  async function playGeneratedAudio() {
    setTtsLoading(true);
    window.speechSynthesis?.cancel();

    try {
      const nextAudioUrl = await getAudioUrl();
      const audio = new Audio(nextAudioUrl);
      audioRef.current = audio;
      audio.onended = () => setPlaying(false);
      audio.onerror = () => {
        setPlaying(false);
        playBrowserTts();
      };
      await audio.play();
      setPlaying(true);
    } catch {
      playBrowserTts();
    } finally {
      setTtsLoading(false);
    }
  }

  return (
    <section className="result-panel show" aria-live="polite">
      <div className="result-header">
        <div>
          <span className="result-kicker">생성 완료 · {result.formatLabel}</span>
          <h2>{result.title}</h2>
          <p>{result.concept}</p>
          {result.generationNotice && <small>{result.generationNotice}</small>}
        </div>
        <span className="duration-badge">{result.duration}</span>
      </div>

      <div className="audio-player">
        <button
          className="play-button"
          type="button"
          aria-label={playing ? "음성 정지" : "대본 읽기"}
          onClick={handleSpeechToggle}
          disabled={ttsLoading}
        >
          {ttsLoading ? "..." : playing ? "II" : "▶"}
        </button>
        <div className="waveform" aria-hidden="true">
          {Array.from({ length: 15 }).map((_, index) => (
            <span key={index} />
          ))}
        </div>
        <span className="audio-time">
          {ttsLoading ? "TTS 생성 중" : playing ? `재생 중 · ${ttsProvider || "로컬 TTS"}` : audioUrl ? ttsProvider || "로컬 TTS" : "TTS 준비"}
        </span>
      </div>

      <div className="script-toolbar" aria-label="대본 보기 방식">
        <button
          type="button"
          className={viewMode === "segments" ? "selected" : ""}
          onClick={() => setViewMode("segments")}
        >
          섹션 보기
        </button>
        <button
          type="button"
          className={viewMode === "full" ? "selected" : ""}
          onClick={() => setViewMode("full")}
        >
          전체 대본
        </button>
      </div>

      {viewMode === "segments" ? (
        <div className="segment-list">
          {result.segments.map((segment) => (
            <article className="segment-card" key={`${segment.type}-${segment.title}`}>
              <span>{segment.title}</span>
              <p>{segment.text}</p>
            </article>
          ))}
        </div>
      ) : (
        <article className="full-script-card">
          <span>전체 대본</span>
          <pre>{result.script}</pre>
        </article>
      )}

      <div className="result-grid">
        <article className="result-card">
          <span>예상 청취자 질문</span>
          <ul>
            {result.listenerComments.map((comment) => (
              <li key={comment}>
                <strong>{comment}</strong>
              </li>
            ))}
          </ul>
        </article>
        <article className="result-card">
          <span>추천 음악</span>
          <ul>
            {result.music.map((music) => (
              <li key={music.title}>
                <strong>{music.title}</strong>
                <em>{music.mood}</em>
              </li>
            ))}
          </ul>
        </article>
      </div>
    </section>
  );
}

function VoiceCloneTester() {
  const [voiceFile, setVoiceFile] = useState(null);
  const [sampleText, setSampleText] = useState(
    "안녕하세요. 온에어 목소리 테스트입니다. 짧은 문장으로 먼저 확인해볼게요."
  );
  const [loading, setLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState("");
  const [message, setMessage] = useState("Coqui XTTS는 CPU에서 느릴 수 있어 짧은 문장으로 먼저 테스트합니다.");
  const testAudioRef = useRef(null);

  function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error("음성 샘플 파일을 읽지 못했습니다."));
      reader.readAsDataURL(file);
    });
  }

  async function handleVoiceTest() {
    if (!voiceFile) {
      setMessage("먼저 목소리 샘플 파일을 선택해주세요.");
      return;
    }

    setLoading(true);
    setAudioUrl("");
    setMessage("목소리 샘플을 보내고 XTTS 테스트 음성을 준비하는 중입니다.");

    try {
      const audioBase64 = await readFileAsDataUrl(voiceFile);
      const response = await fetch("/api/voice-test", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          fileName: voiceFile.name,
          mimeType: voiceFile.type,
          audioBase64,
          text: sampleText,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "XTTS 테스트 생성에 실패했습니다.");
      }

      setAudioUrl(data.audioUrl);
      setMessage(`${data.provider} 테스트 음성이 생성되었습니다.`);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  function playVoiceTest() {
    if (!audioUrl) return;

    testAudioRef.current?.pause();
    const audio = new Audio(audioUrl);
    testAudioRef.current = audio;
    audio.play();
  }

  return (
    <section className="voice-panel" aria-label="내 목소리 XTTS 테스트">
      <div className="voice-panel-header">
        <div>
          <span>Voice Clone Test</span>
          <h2>내 목소리로 10초 테스트</h2>
        </div>
        <strong>Coqui XTTS · CPU</strong>
      </div>
      <div className="voice-controls">
        <label className="voice-file">
          <span>목소리 샘플</span>
          <input
            type="file"
            accept="audio/*"
            onChange={(event) => setVoiceFile(event.target.files?.[0] || null)}
          />
        </label>
        <label className="voice-text">
          <span>테스트 문장</span>
          <textarea value={sampleText} onChange={(event) => setSampleText(event.target.value)} />
        </label>
      </div>
      <div className="voice-actions">
        <p>{voiceFile ? voiceFile.name : message}</p>
        <div>
          {audioUrl && (
            <button type="button" className="ghost-button" onClick={playVoiceTest}>
              테스트 재생
            </button>
          )}
          <button type="button" className="make-button" onClick={handleVoiceTest} disabled={loading}>
            {loading ? "생성 중" : "목소리 테스트"}
          </button>
        </div>
      </div>
      {voiceFile && <p className="voice-message">{message}</p>}
    </section>
  );
}

function FloatingCards() {
  return (
    <>
      <article className="floating-card floating-card-left" aria-hidden="true">
        <div className="mini-art mini-purple">AI</div>
        <strong>Script Studio</strong>
        <span>뉴스, 토크, 오프닝 자동 구성</span>
      </article>
      <article className="floating-card floating-card-right" aria-hidden="true">
        <div className="mini-art mini-teal">FM</div>
        <strong>Music Match</strong>
        <span>분위기에 맞는 배경음 추천</span>
      </article>
    </>
  );
}

function Hero({
  topic,
  tone,
  broadcastFormat,
  language,
  durationMinutes,
  source,
  loading,
  error,
  onTopicChange,
  onToneChange,
  onFormatChange,
  onLanguageChange,
  onDurationChange,
  onSourceChange,
  onPickTopic,
  onGenerate,
  stepVisible,
  activeStep,
  completed,
  result,
}) {
  return (
    <main className="hero">
      <FloatingCards />
      <section className="hero-copy">
        <div className="eyebrow">
          <span />
          AI Radio Generator
        </div>
        <h1>
          만들고 싶은 방송을
          <br />
          <em>한 문장으로</em>
        </h1>
        <p>
          주제와 형식을 고르면 방송 구성, 대본, 청취자 코멘트, 음악 추천까지 이어지는
          <br />
          개인 맞춤형 AI 라디오 제작 데모입니다.
        </p>
      </section>

      <PromptBox
        topic={topic}
        tone={tone}
        broadcastFormat={broadcastFormat}
        language={language}
        durationMinutes={durationMinutes}
        source={source}
        loading={loading}
        onTopicChange={onTopicChange}
        onToneChange={onToneChange}
        onFormatChange={onFormatChange}
        onLanguageChange={onLanguageChange}
        onDurationChange={onDurationChange}
        onSourceChange={onSourceChange}
        onPickTopic={onPickTopic}
        onGenerate={onGenerate}
      />
      {error && <p className="error-message">{error}</p>}
      <GenerationSteps visible={stepVisible} activeStep={activeStep} completed={completed} />
      <ResultPanel result={result} />
      <VoiceCloneTester />
    </main>
  );
}

function RecentBroadcasts() {
  return (
    <section className="recent" id="recent">
      <div className="section-heading">
        <h2>최근 생성 방송</h2>
        <a href="#generate">새 방송 만들기</a>
      </div>
      <div className="broadcast-grid">
        {recentBroadcasts.map((broadcast) => (
          <article className="broadcast-card" key={broadcast.title}>
            <div className={`card-art ${broadcast.className}`}>{broadcast.icon}</div>
            <div className="card-body">
              <strong>{broadcast.title}</strong>
              <span>{broadcast.meta}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default function App() {
  const [topic, setTopic] = useState("");
  const [tone, setTone] = useState("casual");
  const [broadcastFormat, setBroadcastFormat] = useState("deep_dive");
  const [language, setLanguage] = useState("ko");
  const [durationMinutes, setDurationMinutes] = useState(5);
  const [source, setSource] = useState("");
  const [stepVisible, setStepVisible] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [completed, setCompleted] = useState(false);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const timersRef = useRef([]);

  useEffect(() => {
    return () => {
      timersRef.current.forEach((timer) => window.clearTimeout(timer));
    };
  }, []);

  function clearTimers() {
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];
  }

  function startStepAnimation() {
    generationSteps.forEach((_, index) => {
      const timer = window.setTimeout(() => {
        setActiveStep(index);
      }, index * 500);

      timersRef.current.push(timer);
    });
  }

  function normalizeResult(data, fallbackTopic) {
    return {
      title: data.title ?? `${fallbackTopic} 방송`,
      topic: data.topic ?? fallbackTopic,
      concept: data.concept ?? "",
      formatLabel: data.formatLabel ?? "심층 분석",
      script: data.script ?? "",
      segments: data.segments ?? [],
      listenerComments: data.listenerComments ?? [],
      music: data.music ?? [],
      audioUrl: data.audioUrl ?? "",
      duration: data.duration ?? "약 5분",
      cuesheet: data.cuesheet ?? [],
      generationProvider: data.generationProvider ?? "offline",
      generationNotice: data.generationNotice ?? "",
    };
  }

  function handlePickTopic(nextTopic) {
    setTopic(nextTopic);
  }

  async function handleGenerate(event) {
    event.preventDefault();

    const nextTopic = topic.trim() || "오늘의 서울 핫플과 주말 산책 코스";
    setTopic(nextTopic);
    setResult(null);
    setError("");
    setCompleted(false);
    setActiveStep(0);
    setStepVisible(true);
    setLoading(true);
    clearTimers();
    startStepAnimation();

    try {
      const responsePromise = fetch("/api/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          topic: nextTopic,
          tone,
          format: broadcastFormat,
          language,
          durationMinutes,
          source: source.trim(),
        }),
      });
      const [response] = await Promise.all([responsePromise, wait(1900)]);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "방송 생성 요청에 실패했습니다.");
      }

      const data = await response.json();
      setActiveStep(generationSteps.length - 1);
      setCompleted(true);
      setResult(normalizeResult(data, nextTopic));
    } catch (requestError) {
      setError(requestError.message);
      setStepVisible(false);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-shell">
      <Header />
      <Hero
        topic={topic}
        tone={tone}
        broadcastFormat={broadcastFormat}
        language={language}
        durationMinutes={durationMinutes}
        source={source}
        loading={loading}
        error={error}
        onTopicChange={setTopic}
        onToneChange={setTone}
        onFormatChange={setBroadcastFormat}
        onLanguageChange={setLanguage}
        onDurationChange={setDurationMinutes}
        onSourceChange={setSource}
        onPickTopic={handlePickTopic}
        onGenerate={handleGenerate}
        stepVisible={stepVisible}
        activeStep={activeStep}
        completed={completed}
        result={result}
      />
      <RecentBroadcasts />
      <button className="help-button" type="button" aria-label="도움말">
        ?
      </button>
    </div>
  );
}

