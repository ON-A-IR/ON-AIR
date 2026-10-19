﻿import { useEffect, useRef, useState } from "react";

import { Play, Pause, Download, LoaderCircle, Clock3, RotateCcw, RotateCw, Radio, FolderOpen, Trash2, Plus, Home, Search, Mic2, Headphones, AudioLines, Lightbulb, MessagesSquare, Check, Languages, Link2, PanelLeftClose, PanelLeftOpen, LogOut } from "lucide-react";
import radioSamples from "../public/samples/scripts.json";
import sampleVoiceVersions from "../public/samples/voice-manifest.json";
import AuthGate from "./AuthGate";

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
    Icon: Headphones,
    title: "이야기 라디오",
    description: "두 진행자가 익숙한 일상에서 이야기를 꺼내고, 궁금한 점을 하나씩 풀어갑니다.",
  },
  {
    value: "summary",
    Icon: AudioLines,
    title: "한눈에 브리핑",
    description: "한 진행자가 꼭 알아둘 내용을 골라, 듣기 편한 순서로 짧고 명확하게 전합니다.",
  },
  {
    value: "critique",
    Icon: Lightbulb,
    title: "생각의 주파수",
    description: "한 진행자가 좋은 점과 아쉬운 점을 짚고, 놓치기 쉬운 질문을 함께 생각해봅니다.",
  },
  {
    value: "debate",
    Icon: MessagesSquare,
    title: "두 가지 시선",
    description: "두 진행자가 같은 주제를 다른 관점에서 바라보며, 의견이 갈리는 이유를 나눕니다.",
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

function Header({ user, onLogout, collapsed, onToggle }) {
  const [active, setActive] = useState(() => window.location.hash || "#home");
  useEffect(() => {
    const update = () => setActive(window.location.hash || "#home");
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  const menus = [{ href: "#home", label: "홈", Icon: Home }, { href: "#explore", label: "탐색", Icon: Search }, { href: "#generate", label: "만들기", Icon: Mic2 }];
  return (
    <header className="app-sidebar">
      <div className="sidebar-heading"><a className="brand" href="#home" aria-label="On-AI-r 홈">
        On-AI-r
      </a>
      <button type="button" className="sidebar-toggle" onClick={onToggle} aria-label={collapsed ? "메뉴 펼치기" : "메뉴 접기"} aria-expanded={!collapsed} aria-controls="sidebar-navigation" title={collapsed ? "메뉴 펼치기" : "메뉴 접기"}>{collapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}</button></div>
      <nav id="sidebar-navigation" className="sidebar-links" aria-label="주요 메뉴">
        {menus.map(({ href, label, Icon }) => <a key={href} href={href} aria-label={label} data-tooltip={label} className={active === href ? "selected" : ""} aria-current={active === href ? "location" : undefined} onClick={() => setActive(href)}><Icon size={20} aria-hidden="true" /><span>{label}</span></a>)}
      </nav>
      <div className="sidebar-account"><span>{user.username}</span><button type="button" onClick={onLogout} aria-label="로그아웃" title="로그아웃"><LogOut size={16} aria-hidden="true" /><span>로그아웃</span></button></div>
    </header>
  );
}

function SourceEditor({ sources, onChange, disabled, searchOnly = false }) {
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
  return <section className={`source-editor ${searchOnly ? "home-source-search" : ""}`} aria-label="방송 출처">
    {!searchOnly && <h2>출처 <small>{sources.filter((item) => item.selected).length}개 선택</small></h2>}
    <div className="web-search">
      <input aria-label="웹 검색어" placeholder="웹에서 소스 검색" value={query} disabled={searching || disabled} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => {if (e.key === "Enter") { e.preventDefault(); search(); }}} maxLength={200} />
      <button type="button" disabled={searching || disabled || query.trim().length < 2} onClick={search}>{searchOnly && (searching ? <LoaderCircle className="audio-loading-icon" size={16} aria-hidden="true" /> : <Search size={16} aria-hidden="true" />)}{searching ? "조사 중…" : searchOnly ? "검색" : "웹 검색"}</button>
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
    {!searchOnly && <><details className="manual-source"><summary>자료 직접 추가</summary><div className="source-entry">
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
    </li>)}</ul></>}
  </section>;
}

function FormatSelector({ broadcastFormat, onFormatChange }) {
  return (
    <section className="format-section" aria-label="방송 형식">
      <h2>방송 스타일</h2>
      <div className="format-grid">
        {formatOptions.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`format-card ${broadcastFormat === option.value ? "selected" : ""}`}
            aria-pressed={broadcastFormat === option.value}
            onClick={() => onFormatChange(option.value)}
          >
            <div className="format-topline"><option.Icon size={19} strokeWidth={1.7} aria-hidden="true" /><Check className="format-check" size={15} aria-hidden="true" /></div>
            <span className="format-name">{option.title}</span>
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
          aria-pressed={tone === option.value}
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
        <span><Languages size={14} aria-hidden="true" /> 언어 선택</span>
        <select value={language} onChange={(event) => onLanguageChange(event.target.value)}>
          <option value="ko">한국어</option>
          <option value="en">English</option>
        </select>
      </label>
      <label>
        <span><Clock3 size={14} aria-hidden="true" /> 길이</span>
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
        <span><Link2 size={14} aria-hidden="true" /> 참고 메모</span>
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
    <form className="prompt-box creation-form" id="generate" onSubmit={onGenerate}>
      <label className="topic-label" htmlFor="topic">
        <Mic2 size={16} aria-hidden="true" /> 방송 주제
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
          {loading ? <LoaderCircle className="audio-loading-icon" size={17} aria-hidden="true" /> : <Radio size={17} aria-hidden="true" />}
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
    const pause = () => audioRef.current?.pause();
    window.addEventListener("onair-sample-play", pause);
    return () => window.removeEventListener("onair-sample-play", pause);
  }, []);

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
      throw new Error(errorData.detail || "음성 생성에 실패했습니다.");
    }

    const data = await response.json();
    setAudioUrl(data.audioUrl);
    setTtsProvider(data.provider || "로컬 TTS");
    return data.audioUrl;
  }

  async function playGeneratedAudio() {
    window.dispatchEvent(new Event("onair-main-play"));
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
        setTtsError("음성 파일을 재생하지 못했습니다.");
      };
      await audio.play();
      setPlaying(true);
    } catch (error) {
      setPlaying(false);
      setTtsError(error.message || "음성을 재생하지 못했습니다.");
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
    window.dispatchEvent(new Event("onair-main-play"));
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
          <span className="result-kicker">생성 완료 · {formatOptions.find((option) => option.value === result.broadcastFormat)?.title || result.formatLabel}</span>
          <h2>{result.title}</h2>
          <div className="result-meta"><span>{result.generationProvider === "ollama" ? "Ollama" : "대본 생성"}</span><span><Clock3 size={14} aria-hidden="true" />{result.duration}</span></div>
          {result.generationNotice && <small>{result.generationNotice}</small>}
        </div>
      </div>

      <div className="radio-transport">
        <div className="transport-heading"><strong>방송 오디오</strong><span>{ttsLoading || downloading ? "음성 준비 중" : ttsProvider || "AI 음성"}</span></div>
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


function FloatingCards({ showAll = false }) {
  const [samples] = useState(() => {
    if (showAll) return radioSamples;
    let previous = [];
    try { previous = JSON.parse(sessionStorage.getItem("onair.sample-pair") || "[]"); } catch {}
    if (!Array.isArray(previous)) previous = [];
    const candidates = radioSamples.filter((item) => !previous.includes(item.id));
    const chosen = [];
    while (chosen.length < 2 && candidates.length) chosen.push(candidates.splice(Math.floor(Math.random() * candidates.length), 1)[0]);
    return chosen;
  });
  const [active, setActive] = useState("");
  const [error, setError] = useState("");
  const player = useRef(null);
  useEffect(() => {
    if (!showAll) {
      try { sessionStorage.setItem("onair.sample-pair", JSON.stringify(samples.map((item) => item.id))); } catch {}
    }
    const stop = () => { player.current?.pause(); setActive(""); };
    window.addEventListener("onair-main-play", stop);
    return () => { player.current?.pause(); window.removeEventListener("onair-main-play", stop); };
  }, [samples, showAll]);
  async function preview(sample) {
    if (active === sample.id) { player.current?.pause(); setActive(""); return; }
    player.current?.pause();
    const audio = new Audio(`/samples/${sample.id}.mp3?v=${sampleVoiceVersions[sample.id] || "1"}`);
    player.current = audio;
    audio.onended = () => { if (player.current === audio) setActive(""); };
    audio.onerror = () => { if (player.current === audio) { setActive(""); setError("샘플을 재생하지 못했습니다."); } };
    setError(""); setActive(sample.id);
    window.dispatchEvent(new Event("onair-sample-play"));
    try { await audio.play(); } catch { if (player.current === audio) { setActive(""); setError("샘플을 재생하지 못했습니다."); } }
  }
  return <>
    <div className="sample-previews" aria-label="샘플 방송 탐색">{samples.map((sample, index) => <article key={sample.id} className={`floating-card sample-card floating-card-${index ? "right" : "left"} ${active === sample.id ? "is-playing" : ""}`}>
      <img className="sample-cover" src={`/samples/${sample.id}.png`} alt="" loading={showAll ? "lazy" : "eager"} />
      <button type="button" className="sample-play" aria-pressed={active === sample.id} aria-label={`${sample.title} ${active === sample.id ? "일시 정지" : "미리 듣기"}`} title={active === sample.id ? "일시 정지" : "미리 듣기"} onClick={() => preview(sample)}>{active === sample.id ? <Pause size={22} /> : <Play size={22} />}</button>
      <strong>{sample.title}</strong><span>{sample.format} · {active === sample.id ? "재생 중" : "미리 듣기"}</span>
    </article>)}</div>
    {error && <p className="sample-error" role="alert">{error}</p>}
  </>;
}

const headlineTopics = ["블랙홀", "우주 탐사", "반려식물", "커피의 세계", "영화 속 과학", "도시의 역사", "사진 찍는 법", "돈 관리", "새로운 취미", "계절 음식", "바다 생태계", "세계의 축제", "책 고르는 법", "집 정리", "자전거 여행", "음악의 역사", "디지털 습관", "동네 시장", "미래의 직업", "실패에서 배우는 법"];
const headlineListeners = ["처음 듣는 사람", "중학생", "출근길 직장인", "산책하는 사람", "새 취미를 찾는 사람", "호기심 많은 청취자"];
const headlineApproaches = ["쉽고 재미있게", "일상 예시로", "차분한 대화로", "궁금증을 풀어가며", "두 가지 시선으로", "짧은 이야기로"];

function createHeadline(previous = []) {
  const pick = (items) => items[Math.floor(Math.random() * items.length)];
  for (let attempt = 0; attempt < 100; attempt++) {
    const topic = pick(headlineTopics);
    const listener = pick(headlineListeners);
    const approach = pick(headlineApproaches);
    const patterns = [
      () => `${topic} 이야기를 ${approach} 들려줘`,
      () => `${listener}을 위한 ${topic} 방송`,
      () => `${topic}에 대해 ${approach} 이야기해줘`,
    ];
    const text = pick(patterns)();
    if (!previous.includes(text)) return text;
  }
  return "오늘의 새로운 궁금증을 라디오로 풀어줘";
}

function ExampleHeadline({ paused }) {
  const [headline, setHeadline] = useState("만들고 싶은 방송을");
  const recent = useRef([]);
  const [length, setLength] = useState(0);
  const [deleting, setDeleting] = useState(false);
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(media.matches);
    update(); media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    if (paused || reduced) return;
    const full = length === headline.length;
    const timer = window.setTimeout(() => {
      if (!deleting && full) setDeleting(true);
      else if (deleting && length === 0) {
        const next = createHeadline(recent.current);
        recent.current = [...recent.current, next].slice(-100);
        setHeadline(next);
        setDeleting(false);
      } else setLength((value) => value + (deleting ? -1 : 1));
    }, !deleting && full ? 4200 : deleting && length === 0 ? 450 : deleting ? 38 : 70 + Math.random() * 45);
    return () => window.clearTimeout(timer);
  }, [headline, length, deleting, paused, reduced]);
  return <><span className="headline-example" aria-hidden="true"><span>{headline.slice(0, reduced ? undefined : length) || "\u00a0"}{!reduced && <span className="headline-cursor" />}</span></span><span className="headline-accessible">만들고 싶은 방송을 한 문장으로</span></>;
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
    <main className="hero create-page">
      <section className="hero-copy">
        <div className="eyebrow"><span />AI Radio Generator</div>
        <h1 className="example-heading"><ExampleHeadline paused={loading || !!topic.trim()} /><em>한 문장으로</em></h1>
        <p>주제와 형식을 고르면 방송 구성, 대본, 청취자 코멘트, 음악 추천까지 이어지는<br />개인 맞춤형 AI 라디오 제작 데모입니다.</p>
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
    </main>
  );
}

function RecentBroadcasts({ broadcasts, onLoad, onDelete, onNew, disabled }) {
  return (
    <section className="recent" id="recent">
      <div className="section-heading">
        <h2>저장된 방송</h2>
        <button type="button" disabled={disabled} onClick={onNew}><Plus size={16} /> 새 방송</button>
      </div>
      <div className="broadcast-grid">
        {broadcasts.map((broadcast) => (
          <article className="broadcast-card saved-broadcast" key={broadcast.id}>
            <div className="saved-broadcast-heading"><Radio size={24} /><button type="button" title="삭제" aria-label={`${broadcast.result.title} 삭제`} disabled={disabled} onClick={() => onDelete(broadcast.id)}><Trash2 size={16} /></button></div>
            <div className="card-body">
              <strong>{broadcast.result.title}</strong>
              <span>{new Date(broadcast.savedAt).toLocaleDateString("ko-KR")} · 출처 {broadcast.sources?.filter((item) => item.selected).length || 0}개</span>
              <button type="button" disabled={disabled} onClick={() => onLoad(broadcast)}><FolderOpen size={16} /> 불러오기</button>
            </div>
          </article>
        ))}
      </div>
      {!broadcasts.length && <p className="saved-empty">저장된 방송이 없습니다.</p>}
    </section>
  );
}

const DRAFT_STORAGE_KEY = "onair.draft.v1";
const LIBRARY_STORAGE_KEY = "onair.library.v1";

function readLibrary(key = LIBRARY_STORAGE_KEY) {
  try {
    const stored = window.localStorage.getItem(key);
    if (stored !== null) {
      const items = JSON.parse(stored);
      return Array.isArray(items) ? items.filter((item) => item && typeof item.id === "string" && item.result && typeof item.result.script === "string" && ["segments", "music", "sources", "cuesheet", "listenerComments"].every((key) => Array.isArray(item.result[key]))).slice(0, 30) : [];
    }
    if (key !== LIBRARY_STORAGE_KEY) return [];
    const legacy = readSavedDraft();
    return legacy.result ? [{ ...legacy, id: "legacy-draft", savedAt: new Date().toISOString() }] : [];
  } catch { return []; }
}

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

function Workspace({ user, onLogout }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try { return localStorage.getItem("onair.sidebar-collapsed") === "true"; } catch { return false; }
  });
  const libraryKey = `${LIBRARY_STORAGE_KEY}.user-${user.id}`;
  const [view, setView] = useState(() => ["#generate", "#explore"].includes(window.location.hash) ? window.location.hash : "#home");
  useEffect(() => {
    const update = () => {
      setView(["#generate", "#explore"].includes(window.location.hash) ? window.location.hash : "#home");
      window.dispatchEvent(new Event("onair-main-play"));
      window.dispatchEvent(new Event("onair-sample-play"));
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  const [savedDraft] = useState({});
  const [broadcasts, setBroadcasts] = useState(() => readLibrary(libraryKey));
  const [editorKey, setEditorKey] = useState(0);
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

  function saveLibrary(next) {
    try {
      window.localStorage.setItem(libraryKey, JSON.stringify(next));
      setBroadcasts(next);
      return true;
    } catch {
      setError("방송 저장에 실패했습니다. 브라우저 저장 공간과 권한을 확인해주세요.");
      return false;
    }
  }

  function openBroadcast(item = {}) {
    if (loading) return;
    window.location.hash = "generate";
    clearTimers();
    setSources(item.sources || []); setTopic(item.topic || ""); setSource(item.source || "");
    setTone(item.tone || "casual"); setBroadcastFormat(item.broadcastFormat || "deep_dive");
    setLanguage(item.language || "ko"); setDurationMinutes(item.durationMinutes || 5);
    setResult(item.result || null); setError(""); setStepVisible(false); setCompleted(false); setActiveStep(0);
    setEditorKey((key) => key + 1);
    document.getElementById("generate")?.scrollIntoView({ behavior: "smooth" });
  }

  function deleteBroadcast(id) {
    if (window.confirm("저장된 방송을 삭제할까요?")) saveLibrary(broadcasts.filter((item) => item.id !== id));
  }

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
      formatLabel: data.formatLabel ?? "이야기 라디오",
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
      const nextResult = normalizeResult(data, nextTopic, tone, broadcastFormat);
      setResult(nextResult);
      saveLibrary([{ id: crypto.randomUUID(), savedAt: new Date().toISOString(), sources, topic: nextTopic, tone, broadcastFormat, language, durationMinutes, source, result: nextResult }, ...broadcasts].slice(0, 30));
    } catch (requestError) {
      setError(requestError.message);
      setStepVisible(false);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={`page-shell sidebar-layout separated-pages${sidebarCollapsed ? " sidebar-collapsed" : ""}`}>
      <Header user={user} onLogout={onLogout} collapsed={sidebarCollapsed} onToggle={() => {
        const next = !sidebarCollapsed;
        setSidebarCollapsed(next);
        try { localStorage.setItem("onair.sidebar-collapsed", String(next)); } catch {}
      }} />
      <main className="home-search-page" hidden={view !== "#home"}>
        <div className="home-search-title"><Radio size={22} aria-hidden="true" /><h1>어떤 이야기가 궁금하세요?</h1></div>
        <div className="home-example"><ExampleHeadline paused={view !== "#home" || loading} /></div>
        <SourceEditor searchOnly sources={sources} onChange={setSources} disabled={loading} />
        {!!sources.filter((item) => item.selected).length && <a className="home-create-link" href="#generate">선택한 출처 {sources.filter((item) => item.selected).length}개로 방송 만들기 <Mic2 size={16} /></a>}
      </main>
      <main className="explore-page" hidden={view !== "#explore"}><h1>탐색</h1><h2>미리 듣는 ON-AIR</h2><FloatingCards showAll /></main>
      <div hidden={view !== "#generate"}>
      <h1 className="create-page-heading">방송 만들기</h1>
      <Hero
        sourceEditor={<SourceEditor key={editorKey} sources={sources} onChange={setSources} disabled={loading} />}
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
      <RecentBroadcasts broadcasts={broadcasts} onLoad={openBroadcast} onNew={() => openBroadcast()} onDelete={deleteBroadcast} disabled={loading} />
      </div>
      <button className="help-button" type="button" aria-label="도움말">
        ?
      </button>
    </div>
  );
}

export default function App() {
  return <AuthGate samples={<FloatingCards />}>{(user, onLogout) => <Workspace key={user.id} user={user} onLogout={onLogout} />}</AuthGate>;
}

