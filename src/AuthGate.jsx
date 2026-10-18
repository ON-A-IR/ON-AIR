import { useEffect, useRef, useState } from "react";
import { ArrowRight, LoaderCircle, Radio, X } from "lucide-react";

async function authRequest(path, body) {
  const response = await fetch(`/api/auth/${path}`, { credentials: "same-origin", ...(body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}) });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "요청을 처리하지 못했습니다. 입력 내용을 확인해주세요.");
  return data;
}

export default function AuthGate({ children, samples }) {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const [mode, setMode] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const dialog = useRef(null);
  useEffect(() => {
    let alive = true;
    authRequest("me").then((data) => { if (alive) setUser(data.user); }).catch(() => { if (alive) setError("서버에 연결하지 못했습니다. 백엔드 실행 상태를 확인해주세요."); }).finally(() => { if (alive) setChecking(false); });
    return () => { alive = false; };
  }, []);
  useEffect(() => {
    if (mode && !dialog.current?.open) dialog.current?.showModal();
    if (!mode && dialog.current?.open) dialog.current.close();
  }, [mode]);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      const data = await authRequest(mode, { username, password });
      setPassword("");
      if (mode === "register") { setMode("login"); setNotice("가입이 완료됐습니다. 로그인해주세요."); }
      else { setUser(data.user); setMode(""); window.location.hash = "home"; }
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  async function logout() {
    try {
      await authRequest("logout", {});
      setUser(null); window.location.hash = "home";
    } catch (failure) { window.alert(failure.message); }
  }
  function open(next) { setError(""); setNotice(""); setPassword(""); setMode(next); }
  if (checking) return <div className="auth-check" role="status"><LoaderCircle className="audio-loading-icon" size={24} /> 로그인 확인 중</div>;
  if (user) return children(user, logout);
  return <div className="welcome-page">
    <header className="welcome-header"><a className="brand" href="#">On-AI-r</a><nav aria-label="계정"><button type="button" className="welcome-login" onClick={() => open("login")}>로그인</button><button type="button" className="welcome-signup" onClick={() => open("register")}>회원가입 <ArrowRight size={16} /></button></nav></header>
    <main>
      <section className="welcome-hero">
        <img className="welcome-background" src="/samples/weekend-walk.png" alt="" />
        <div className="welcome-hero-copy"><span className="welcome-onair"><Radio size={16} /> ON-AIR</span><h1>당신의 이야기를<br />라디오로.</h1><p>궁금했던 주제부터 오늘의 작은 발견까지.<br />나만의 방송으로 만들고 들어보세요.</p><button type="button" className="welcome-start" onClick={() => open("register")}>내 방송 시작하기 <ArrowRight size={18} /></button></div>
      </section>
      <section className="welcome-samples"><div className="welcome-section-heading"><h2>먼저, 들어보세요.</h2><button type="button" onClick={() => open("login")}>스튜디오 들어가기 <ArrowRight size={16} /></button></div>{samples}</section>
    </main>
    {error && !mode && <p className="welcome-server-error" role="alert">{error}</p>}
    <footer className="welcome-footer">ON-AIR · 나의 이야기가 방송이 되는 곳</footer>
    <dialog ref={dialog} className="auth-dialog" onCancel={(event) => { if (busy) event.preventDefault(); else setMode(""); }} onClose={() => { if (!busy) setMode(""); }}>
      <div className="auth-dialog-heading"><h2>{mode === "register" ? "ON-AIR 회원가입" : "다시 만나 반가워요"}</h2><button type="button" title="닫기" aria-label="닫기" disabled={busy} onClick={() => setMode("")}><X size={20} /></button></div>
      <form onSubmit={submit}><label>아이디<input autoFocus name="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required minLength={3} maxLength={32} pattern="[A-Za-z0-9_]{3,32}" placeholder="영문·숫자·밑줄 3~32자" disabled={busy} /></label><label>비밀번호<input name="password" type="password" autoComplete={mode === "register" ? "new-password" : "current-password"} value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} maxLength={128} placeholder="8자 이상" disabled={busy} /></label>{error && <p role="alert" className="error-message">{error}</p>}{notice && <p role="status">{notice}</p>}<button className="auth-submit" type="submit" disabled={busy}>{busy ? <LoaderCircle className="audio-loading-icon" size={18} /> : mode === "register" ? "가입하기" : "로그인"}</button></form>
      <button type="button" className="auth-switch" disabled={busy} onClick={() => open(mode === "register" ? "login" : "register")}>{mode === "register" ? "이미 계정이 있어요 · 로그인" : "처음 오셨나요? · 회원가입"}</button>
    </dialog>
  </div>;
}
