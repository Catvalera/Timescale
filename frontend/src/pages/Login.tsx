import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ApiError, auth, session } from "../api";
import AuthLayout from "../components/AuthLayout";
import Field from "../components/Field";

export default function Login() {
  const navigate = useNavigate();
  const notice = (useLocation().state as { notice?: string } | null)?.notice;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      session.setPending(await auth.login(email, password));
      navigate("/verify");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось войти");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Вход" lead="После пароля мы отправим на почту код подтверждения.">
      {notice && <p className="notice">{notice}</p>}
      <form className="form" onSubmit={submit} noValidate={false}>
        <Field label="Почта" name="email" type="email" autoComplete="email" required
               value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field label="Пароль" name="password" type="password" autoComplete="current-password" required
               value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn--primary" disabled={busy}>{busy ? "Проверяем…" : "Получить код"}</button>
      </form>
      <p className="switch">Нет аккаунта? <Link to="/register">Зарегистрироваться</Link></p>
    </AuthLayout>
  );
}
