import type { ReactNode } from "react";

export default function AuthLayout({ title, lead, children }: { title: string; lead?: ReactNode; children: ReactNode }) {
  return (
    <main className="auth">
      <div className="auth__brand">
        <span className="brand">Timescale</span>
        <p className="auth__tagline">Загрузка замеров из CSV и сводная статистика по каждому файлу</p>
      </div>
      <section className="auth__panel" aria-labelledby="auth-title">
        <h1 id="auth-title">{title}</h1>
        {lead && <p className="lead">{lead}</p>}
        {children}
      </section>
    </main>
  );
}
