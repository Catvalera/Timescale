import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, auth, session } from "../api";
import AuthLayout from "../components/AuthLayout";
import Field from "../components/Field";

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", nickname: "", email: "", password: "", password2: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (form.password !== form.password2) {
      setError("Пароли не совпадают");
      return;
    }
    setBusy(true);
    try {
      const { password2: _, ...body } = form;
      session.setPending(await auth.register(body));
      navigate("/verify");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось зарегистрироваться");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Регистрация" lead="На указанную почту придёт код — без него аккаунт не активируется.">
      <form className="form" onSubmit={submit}>
        <Field label="ФИО" name="full_name" autoComplete="name" required minLength={2}
               value={form.full_name} onChange={set("full_name")} />
        <Field label="Никнейм" name="nickname" autoComplete="username" required
               pattern="[A-Za-z0-9_.\-]{3,32}" hint="3–32 символа: латиница, цифры, «_», «.», «-»"
               value={form.nickname} onChange={set("nickname")} />
        <Field label="Почта" name="email" type="email" autoComplete="email" required
               value={form.email} onChange={set("email")} />
        <Field label="Пароль" name="password" type="password" autoComplete="new-password" required minLength={8}
               hint="Не короче 8 символов, буквы и цифры" value={form.password} onChange={set("password")} />
        <Field label="Пароль ещё раз" name="password2" type="password" autoComplete="new-password" required
               value={form.password2} onChange={set("password2")} />
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn--primary" disabled={busy}>{busy ? "Отправляем код…" : "Зарегистрироваться"}</button>
      </form>
      <p className="switch">Уже есть аккаунт? <Link to="/login">Войти</Link></p>
    </AuthLayout>
  );
}
