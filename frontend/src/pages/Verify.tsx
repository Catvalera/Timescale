import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ApiError, auth, session, type PendingVerification, type User } from "../api";
import AuthLayout from "../components/AuthLayout";
import CodeInput from "../components/CodeInput";

function secondsLeft(p: PendingVerification) {
  return Math.max(0, Math.ceil(p.resendAfter - (Date.now() - p.sentAt) / 1000));
}

export default function Verify({ onAuthorized }: { onAuthorized: (u: User) => void }) {
  const navigate = useNavigate();
  const [pending, setPending] = useState(session.pending);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const [wait, setWait] = useState(() => (pending ? secondsLeft(pending) : 0));

  useEffect(() => {
    if (!pending) return;
    const t = setInterval(() => setWait(secondsLeft(pending)), 500);
    return () => clearInterval(t);
  }, [pending]);

  useEffect(() => {
    if (code.length === 6 && !busy) void submit(code);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);

  if (!pending) return <Navigate to="/login" replace />;

  async function submit(value: string) {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const user = await auth.verify(pending!, value);
      onAuthorized(user);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось проверить код");
      setCode("");
      if (err instanceof ApiError && err.status === 401) {
        session.setPending(null);
        navigate("/login", { replace: true, state: { notice: "Время на ввод кода вышло. Войдите снова." } });
      }
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setError("");
    setInfo("");
    try {
      const next = await auth.resend(pending!);
      session.setPending(next);
      setPending(next);
      setCode("");
      setInfo("Новый код отправлен. Предыдущий больше не действует.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось отправить код");
    }
  }

  const registration = pending.purpose === "registration";
  return (
    <AuthLayout
      title={registration ? "Подтвердите почту" : "Код для входа"}
      lead={<>Мы отправили 6-значный код на <b>{pending.email}</b>. Он действует 10 минут.</>}
    >
      <form className="form" onSubmit={(e) => { e.preventDefault(); void submit(code); }}>
        <CodeInput value={code} onChange={setCode} disabled={busy} invalid={Boolean(error)} />
        {error && <p className="error" role="alert">{error}</p>}
        {info && <p className="notice" role="status">{info}</p>}
        <button className="btn btn--primary" disabled={busy || code.length !== 6}>
          {busy ? "Проверяем…" : registration ? "Подтвердить почту" : "Войти"}
        </button>
      </form>
      <p className="switch">
        {wait > 0
          ? <>Отправить код ещё раз можно через {wait} с</>
          : <button type="button" className="link" onClick={resend}>Отправить код ещё раз</button>}
      </p>
      <p className="switch"><Link to="/login" onClick={() => session.setPending(null)}>Начать заново</Link></p>
    </AuthLayout>
  );
}
