﻿import { useEffect, useRef, useState } from "react";

import { Play, Pause, Download, LoaderCircle, Clock3, RotateCcw, RotateCw } from "lucide-react";

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

function SourceEditor({ sources, onChange, disabled }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [searched, setSearched] = useState(false);
  async function search() {
    if (searching || query.trim().length < 2) return;
    setSearching(true); setSearchError(""); setSearched(false); setResults([]);
    try {
      const response = await fetch("/api/sources/search", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({query: query.trim()})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "검색에 실패했습니다.");
      setResults(data.results); setSearched(true);
    } catch (error) { setSearchError(error.message); }
    finally { setSearching(false); }
  }
  function toggleResult(item) {
    const existing = sources.find((s) => s.url === item.url);
    if (existing) onChange(sources.map((s) => s.id === existing.id ? {...s, selected: !s.selected} : s));
    else if (sources.length < 10) onChange([...sources, {id: crypto.randomUUID(), title: item.title, url: item.url, text: "", selected: true}]);
  }
  const [kind, setKind] = useState("url");
  const [value, setValue] = useState("");
  const [title, setTitle] = useState("");
  return <section className="source-editor" aria-label="방송 출처">
    <h2>출처 <small>{sources.filter((item) => item.selected).length}개 선택</small></h2>
    <div className="web-search">
      <input aria-label="웹 검색어" placeholder="웹에서 소스 검색" value={query} disabled={searching || disabled} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => {if (e.key === "Enter") { e.preventDefault(); search(); }}} maxLength={200} />
      <button type="button" disabled={searching || disabled || query.trim().length < 2} onClick={search}>{searching ? "조사 중…" : "웹 검색"}</button>
    </div>
    {searching && <p role="status">웹사이트를 조사 중입니다…</p>}
    {searchError && <p role="alert">{searchError}</p>}
    {searched && !results.length && <p>검색 결과가 없습니다. 다른 검색어로 검색해주세요.</p>}
    {!!results.length && <div className="web-results">
      <div className="web-results-header"><strong>검색 결과</strong><button type="button" disabled={disabled} onClick={() => {
        const next = [...sources];
        for (const item of results) { const index = next.findIndex((s) => s.url === item.url); if (index >= 0) next[index] = {...next[index], selected: true}; else if (next.length < 10) next.push({id: crypto.randomUUID(), title: item.title, url: item.url, text: "", selected: true}); }
        onChange(next);
      }}>모두 선택</button></div>
      {results.map((item) => <article key={item.url} className="web-result">
        <input type="checkbox" aria-label={`${item.title} 선택`} checked={sources.some((s) => s.url === item.url && s.selected)} disabled={disabled || (sources.length >= 10 && !sources.some((s) => s.url === item.url))} onChange={() => toggleResult(item)} />
        <div><a href={item.url} target="_blank" rel="noreferrer">{item.title}</a><small>{item.domain}</small><p>{item.snippet}</p></div>
      </article>)}
    </div>}
    <details className="manual-source"><summary>자료 직접 추가</summary><div className="source-entry">
      <select aria-label="소스 종류" value={kind} onChange={(e) => setKind(e.target.value)}><option value="url">웹사이트</option><option value="text">붙여 넣은 자료</option></select>
      <input aria-label="자료 제목" placeholder="자료 제목 (선택)" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
      <textarea aria-label="소스 내용" placeholder={kind === "url" ? "https://..." : "자료 본문"} value={value} onChange={(e) => setValue(e.target.value)} maxLength={kind === "url" ? 2000 : 12000} />
      <button type="button" disabled={disabled || !value.trim() || sources.length >= 10} onClick={() => {
        onChange([...sources, {id: crypto.randomUUID(), title: title.trim(), url: kind === "url" ? value.trim() : "", text: kind === "text" ? value.trim() : "", selected: true}]);
        setValue(""); setTitle("");
      }}>소스 추가</button>
    </div></details>
    <ul>{sources.map((item) => <li key={item.id}>
      <label><input type="checkbox" checked={item.selected} disabled={disabled} onChange={() => onChange(sources.map((s) => s.id === item.id ? {...s, selected: !s.selected} : s))} /><span>{item.title || item.url || item.text.slice(0, 60)}</span></label>
      <button type="button" aria-label="소스 삭제" disabled={disabled} onClick={() => onChange(sources.filter((s) => s.id !== item.id))}>×</button>
    </li>)}</ul>
  </section>;
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
  sourceEditor,
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
      <label className="topic-label" htmlFor="topic">
        방송 주제
      </label>
      <textarea
        id="topic"
        value={topic}
        onChange={(event) => onTopicChange(event.target.value)}
        placeholder="방송 주제 입력 (비워두면 선택한 출처를 기반으로 생성)"
      />
      {sourceEditor}
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
  const [ttsError, setTtsError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [position, setPosition] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [viewMode, setViewMode] = useState("full");
  const audioRef = useRef(null);
  const audioBlobRef = useRef(null);

  useEffect(() => {
    window.speechSynthesis?.cancel();
    audioRef.current?.pause();
    audioRef.current = null;
    if (audioBlobRef.current) URL.revokeObjectURL(audioBlobRef.current);
    audioBlobRef.current = null;
    setPlaying(false);
    setTtsLoading(false);
    setAudioUrl(result?.audioUrl || "");
    setTtsProvider("");
    setTtsError("");
    setPosition(0);
    setAudioDuration(0);
    setViewMode("segments");

    return () => {
      window.speechSynthesis?.cancel();
      audioRef.current?.pause();
      if (audioBlobRef.current) URL.revokeObjectURL(audioBlobRef.current);
      audioBlobRef.current = null;
    };
  }, [result]);

  if (!result) return null;

  function handleSpeechToggle() {
    if (playing) {
      audioRef.current?.pause();
      window.speechSynthesis.cancel();
      setPlaying(false);
      return;
    }

    playGeneratedAudio();
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
        tone: result.tone,
        format: result.broadcastFormat,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || "Piper 음성 생성에 실패했습니다.");
    }

    const data = await response.json();
    setAudioUrl(data.audioUrl);
    setTtsProvider(data.provider || "로컬 TTS");
    return data.audioUrl;
  }

  async function playGeneratedAudio() {
    setTtsLoading(true);
    setTtsError("");
    window.speechSynthesis?.cancel();

    try {
      const nextAudioUrl = await getAudioUrl();
      // A local blob supports seeking even when the server ignores Range requests.
      if (!audioRef.current) {
        const response = await fetch(nextAudioUrl);
        if (!response.ok) throw new Error("음성 파일을 불러오지 못했습니다.");
        audioBlobRef.current = URL.createObjectURL(await response.blob());
        audioRef.current = new Audio(audioBlobRef.current);
      }
      const audio = audioRef.current;
      audioRef.current = audio;
      audio.playbackRate = playbackRate;
      audio.onloadedmetadata = () => setAudioDuration(Number.isFinite(audio.duration) ? audio.duration : 0);
      audio.ontimeupdate = () => setPosition(audio.currentTime);
      audio.onplay = () => setPlaying(true);
      audio.onpause = () => setPlaying(false);
      audio.onended = () => setPlaying(false);
      audio.onerror = () => {
        setPlaying(false);
        setTtsError("Piper WAV 파일을 재생하지 못했습니다.");
      };
      await audio.play();
      setPlaying(true);
    } catch (error) {
      setPlaying(false);
      setTtsError(error.message || "Piper 음성을 재생하지 못했습니다.");
    } finally {
      setTtsLoading(false);
    }
  }

  function seekAudio(seconds) {
    if (!audioRef.current || !audioDuration) return;
    const next = Math.min(audioDuration, Math.max(0, seconds));
    audioRef.current.currentTime = next;
    setPosition(next);
  }

  function pointerTime(event) {
    const bounds = event.currentTarget.getBoundingClientRect();
    return Math.max(0, Math.min(1, (event.clientX - bounds.left) / Math.max(1, bounds.width))) * audioDuration;
  }

  async function playFromSelection(seconds) {
    seekAudio(seconds);
    if (!audioRef.current || !audioDuration) return;
    setTtsError("");
    try {
      await audioRef.current.play();
    } catch {
      setPlaying(false);
      setTtsError("선택한 위치에서 재생하지 못했습니다. 재생 버튼을 눌러주세요.");
    }
  }

  function audioTime(seconds) {
    const value = Math.max(0, Math.floor(seconds || 0));
    return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
  }

  async function downloadMp3() {
    setDownloading(true);
    setTtsError("");
    try {
      const url = await getAudioUrl();
      const response = await fetch("/api/audio/mp3", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({audioUrl: url}),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "MP3 다운로드에 실패했습니다.");
      }
      const blobUrl = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = `${(result.title || "방송").replace(/[\\/:*?"<>|]/g, "_")}.mp3`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 60000);
    } catch (error) {
      setTtsError(error.message || "MP3 다운로드에 실패했습니다.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <section className="result-panel show" aria-live="polite">
      <div className="result-header">
        <div>
          <span className="result-kicker">생성 완료 · {result.formatLabel}</span>
          <h2>{result.title}</h2>
          <div className="result-meta"><span>{result.generationProvider === "ollama" ? "Ollama" : "대본 생성"}</span><span><Clock3 size={14} aria-hidden="true" />{result.duration}</span></div>
          {result.generationNotice && <small>{result.generationNotice}</small>}
        </div>
      </div>

      <div className="radio-transport">
        <div className="transport-heading"><strong>방송 오디오</strong><span>{ttsLoading || downloading ? "음성 준비 중" : ttsProvider || "Piper"}</span></div>
        <input className="audio-seek" type="range" aria-label="재생 위치" aria-valuetext={`${audioTime(position)} / ${audioTime(audioDuration)}`} min={0} max={audioDuration || 1} step={0.1} value={position} disabled={!audioDuration || ttsLoading || downloading}
          onChange={(event) => seekAudio(Number(event.target.value))}
          onPointerDown={(event) => {
            if (event.button !== 0 || !audioDuration) return;
            event.preventDefault();
            event.currentTarget.focus();
            event.currentTarget.setPointerCapture(event.pointerId);
            seekAudio(pointerTime(event));
          }}
          onPointerMove={(event) => {
            event.currentTarget.title = audioTime(pointerTime(event));
            if (event.currentTarget.hasPointerCapture(event.pointerId)) seekAudio(pointerTime(event));
          }}
          onPointerUp={(event) => {
            if (!event.currentTarget.hasPointerCapture(event.pointerId)) return;
            const seconds = pointerTime(event);
            event.currentTarget.releasePointerCapture(event.pointerId);
            playFromSelection(seconds);
          }}
          onKeyUp={(event) => {
            if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End", "PageUp", "PageDown", "Enter", " "].includes(event.key)) {
              playFromSelection(Number(event.currentTarget.value));
            }
          }} />
        <div className="transport-time"><span>{audioTime(position)} / {audioTime(audioDuration)}</span><span>{playing ? "재생 중" : audioDuration ? "일시 정지" : "재생 준비"}</span></div>
        <div className="transport-controls">
          <label className="audio-speed"><span>배속</span><select aria-label="재생 배속" value={playbackRate} onChange={(event) => {
            const rate = Number(event.target.value); setPlaybackRate(rate);
            if (audioRef.current) audioRef.current.playbackRate = rate;
          }}>{[0.75, 1, 1.25, 1.5, 2].map((rate) => <option key={rate} value={rate}>{rate}×</option>)}</select></label>
          <div className="transport-center">
          <button type="button" className="audio-skip" title="10초 뒤로" aria-label="10초 뒤로" disabled={!audioDuration || ttsLoading} onClick={() => seekAudio(position - 10)}><RotateCcw size={21} /><small>10</small></button>
        <button
          className="play-button"
          type="button"
          aria-label={playing ? "음성 정지" : "대본 읽기"}
          title={playing ? "일시 정지" : "재생"}
          onClick={handleSpeechToggle}
          disabled={ttsLoading || downloading}
        >
          {ttsLoading ? <LoaderCircle className="audio-loading-icon" size={20} /> : playing ? <Pause size={20} /> : <Play size={20} />}
        </button>
          <button type="button" className="audio-skip" title="10초 앞으로" aria-label="10초 앞으로" disabled={!audioDuration || ttsLoading} onClick={() => seekAudio(position + 10)}><RotateCw size={21} /><small>10</small></button>
          </div>
          <span className="transport-end"><Clock3 size={16} aria-hidden="true" />{audioTime(audioDuration)}</span>
        </div>
      </div>
      {ttsError && <p className="error-message audio-error">{ttsError}</p>}

      <div className="result-actions">
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
      <button className="mp3-download-button" type="button" onClick={downloadMp3} disabled={downloading || ttsLoading}>
        {downloading ? <LoaderCircle className="audio-loading-icon" size={16} aria-hidden="true" /> : <Download size={16} aria-hidden="true" />}
        {downloading ? "MP3 준비 중…" : "MP3 다운로드"}
      </button>
      </div>
      {result.sources?.length > 0 && <section className="used-sources"><h3>사용한 출처</h3><ul>{result.sources.map((item, index) => <li key={index}>{item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.title}</a> : item.title}</li>)}</ul></section>}

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
  sourceEditor,
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
        sourceEditor={sourceEditor}
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

const DRAFT_STORAGE_KEY = "onair.draft.v1";

function readSavedDraft() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(DRAFT_STORAGE_KEY));
    if (!saved || saved.version !== 1) return {};
    return {
      sources: Array.isArray(saved.sources) ? saved.sources.filter((item) => item && typeof item.id === "string" && typeof item.text === "string" && typeof item.url === "string").slice(0, 10) : [],
      topic: typeof saved.topic === "string" ? saved.topic : "",
      source: typeof saved.source === "string" ? saved.source : "",
      tone: toneOptions.some((item) => item.value === saved.tone) ? saved.tone : "casual",
      broadcastFormat: formatOptions.some((item) => item.value === saved.broadcastFormat) ? saved.broadcastFormat : "deep_dive",
      language: ["ko", "en"].includes(saved.language) ? saved.language : "ko",
      durationMinutes: [5, 10, 15].includes(saved.durationMinutes) ? saved.durationMinutes : 5,
      result: saved.result && typeof saved.result.script === "string" && Array.isArray(saved.result.segments) && Array.isArray(saved.result.music) && Array.isArray(saved.result.sources) && Array.isArray(saved.result.cuesheet) && Array.isArray(saved.result.listenerComments) ? saved.result : null,
    };
  } catch {
    return {};
  }
}

export default function App() {
  const [savedDraft] = useState(readSavedDraft);
  const [sources, setSources] = useState(savedDraft.sources ?? []);
  const [topic, setTopic] = useState(savedDraft.topic ?? "");
  const [tone, setTone] = useState(savedDraft.tone ?? "casual");
  const [broadcastFormat, setBroadcastFormat] = useState(savedDraft.broadcastFormat ?? "deep_dive");
  const [language, setLanguage] = useState(savedDraft.language ?? "ko");
  const [durationMinutes, setDurationMinutes] = useState(savedDraft.durationMinutes ?? 5);
  const [source, setSource] = useState(savedDraft.source ?? "");
  const [stepVisible, setStepVisible] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [completed, setCompleted] = useState(false);
  const [result, setResult] = useState(savedDraft.result ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const timersRef = useRef([]);
  const lastResultRef = useRef(savedDraft.result ?? null);

  useEffect(() => {
    if (result) lastResultRef.current = result;
    try {
      window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify({
        version: 1, sources, topic, tone, broadcastFormat, language,
        durationMinutes, source, result: lastResultRef.current,
      }));
    } catch {
      setError("브라우저 자동 저장에 실패했습니다. 저장 공간과 사이트 저장 권한을 확인해주세요.");
    }
  }, [sources, topic, tone, broadcastFormat, language, durationMinutes, source, result]);

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

  function normalizeResult(data, fallbackTopic, fallbackTone, fallbackFormat) {
    return {
      title: data.title ?? `${fallbackTopic} 방송`,
      topic: data.topic ?? fallbackTopic,
      tone: data.tone ?? fallbackTone,
      broadcastFormat: data.broadcastFormat ?? fallbackFormat,
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
      sources: data.sources ?? [],
    };
  }

  function handlePickTopic(nextTopic) {
    setTopic(nextTopic);
  }

  async function handleGenerate(event) {
    event.preventDefault();

    const nextTopic = topic.trim();
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
          sources: sources.filter((item) => item.selected).map(({title, url, text}) => ({title, url, text})),
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
      setResult(normalizeResult(data, nextTopic, tone, broadcastFormat));
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
        sourceEditor={<SourceEditor sources={sources} onChange={setSources} disabled={loading} />}
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

