import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, auth, data, type ResultRow, type User, type ValueRow } from "../api";
import { fmtDate, fmtNum } from "../format";

type Mode = "all" | "name" | "date" | "avgValue" | "avgTime" | "last10";

const MODES: { id: Mode; label: string }[] = [
  { id: "all", label: "Все" },
  { id: "name", label: "Имя файла" },
  { id: "date", label: "Дата старта" },
  { id: "avgValue", label: "Среднее значение" },
  { id: "avgTime", label: "Среднее время" },
  { id: "last10", label: "10 последних" },
];

const errText = (e: unknown) => (e instanceof ApiError ? e.message : "Что-то пошло не так");

export default function Dashboard({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [results, setResults] = useState<ResultRow[] | null>(null);
  const [values, setValues] = useState<ValueRow[] | null>(null);
  const [filterLabel, setFilterLabel] = useState("Все результаты");
  const [loadError, setLoadError] = useState("");

  const loadAll = useCallback(async () => {
    setLoadError("");
    try {
      setResults(await data.results());
      setFilterLabel("Все результаты");
    } catch (e) {
      setLoadError(errText(e));
    }
  }, []);

  useEffect(() => { void loadAll(); }, [loadAll]);

  async function logout() {
    await auth.logout();
    onLogout();
  }

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">Timescale</span>
        <div className="topbar__user">
          <span className="topbar__who"><b>{user.nickname}</b><span className="muted">{user.full_name}</span></span>
          <button className="btn btn--ghost" onClick={logout}>Выйти</button>
        </div>
      </header>

      <main className="workspace">
        <aside className="side">
          <UploadPanel onUploaded={() => { void loadAll(); setValues(null); }} />
          <FilterPanel
            onResult={(rows, label) => { setResults(rows); setFilterLabel(label); setLoadError(""); }}
            onError={setLoadError}
            onReset={loadAll}
          />
          <MaintenancePanel onCleared={() => { void loadAll(); setValues(null); }} />
        </aside>

        <section className="content">
          <div className="content__head">
            <h2>Результаты</h2>
            <span className="muted">{filterLabel}{results ? ` — ${results.length}` : ""}</span>
          </div>
          {loadError && <p className="error" role="alert">{loadError}</p>}
          <ResultsTable rows={results} />

          <div className="content__head content__head--spaced">
            <h2>Исходные значения</h2>
            <button className="btn btn--ghost" onClick={async () => {
              try { setValues(await data.values()); } catch (e) { setLoadError(errText(e)); }
            }}>{values ? "Обновить" : "Показать"}</button>
          </div>
          {values && <ValuesTable rows={values} />}
        </section>
      </main>
    </div>
  );
}

function UploadPanel({ onUploaded }: { onUploaded: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setStatus(null);
    try {
      setStatus({ ok: true, text: await data.upload(file) });
      setFile(null);
      if (input.current) input.current.value = "";
      onUploaded();
    } catch (err) {
      setStatus({ ok: false, text: errText(err) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={submit}>
      <h3>Загрузить CSV</h3>
      <p className="panel__hint">Формат строк: <code>Date;ExecutionTime;Value</code>. Файл с тем же именем заменит старые данные.</p>
      <div className="file">
        <input ref={input} id="csv-file" className="file__input" type="file" accept=".csv,text/csv" aria-label="CSV-файл"
               onChange={(e) => { setFile(e.target.files?.[0] ?? null); setStatus(null); }} />
        <label htmlFor="csv-file" className="btn btn--ghost">Выбрать файл</label>
        <span className={"file__name" + (file ? "" : " muted")}>{file ? file.name : "Файл не выбран"}</span>
      </div>
      <button className="btn btn--primary" disabled={!file || busy}>{busy ? "Загружаем…" : "Загрузить"}</button>
      {status && <p className={status.ok ? "notice" : "error"} role="status">{status.text}</p>}
    </form>
  );
}

function FilterPanel({ onResult, onError, onReset }: {
  onResult: (rows: ResultRow[], label: string) => void;
  onError: (msg: string) => void;
  onReset: () => void;
}) {
  const [mode, setMode] = useState<Mode>("all");
  const [text, setText] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (mode === "all") { onReset(); return; }
    setBusy(true);
    try {
      switch (mode) {
        case "name": onResult(await data.byFileName(text), `Имя файла содержит «${text}»`); break;
        case "last10": onResult(await data.lastTen(text), `10 последних по «${text}», по дате старта`); break;
        case "date": onResult(await data.byStartDate(from, to), `Старт с ${from} по ${to}`); break;
        case "avgValue": onResult(await data.byAvgValue(+from, +to), `Среднее значение от ${from} до ${to}`); break;
        case "avgTime": onResult(await data.byAvgExecutionTime(+from, +to), `Среднее время от ${from} до ${to}`); break;
      }
    } catch (err) {
      onError(errText(err));
    } finally {
      setBusy(false);
    }
  }

  const isText = mode === "name" || mode === "last10";
  const isRange = mode === "date" || mode === "avgValue" || mode === "avgTime";
  const rangeType = mode === "date" ? "date" : "number";

  return (
    <form className="panel" onSubmit={submit}>
      <h3>Фильтр результатов</h3>
      <div className="modes" role="radiogroup" aria-label="Способ фильтрации">
        {MODES.map((m) => (
          <button key={m.id} type="button" role="radio" aria-checked={mode === m.id}
                  className={"mode" + (mode === m.id ? " mode--on" : "")}
                  onClick={() => { setMode(m.id); setFrom(""); setTo(""); }}>{m.label}</button>
        ))}
      </div>
      {isText && (
        <label className="field">
          <span className="field__label">Часть имени файла</span>
          <input value={text} onChange={(e) => setText(e.target.value)} required placeholder="Text Document _1.csv" />
        </label>
      )}
      {isRange && (
        <div className="range">
          <label className="field">
            <span className="field__label">От</span>
            <input type={rangeType} step="any" value={from} onChange={(e) => setFrom(e.target.value)} required />
          </label>
          <label className="field">
            <span className="field__label">До</span>
            <input type={rangeType} step="any" value={to} onChange={(e) => setTo(e.target.value)} required />
          </label>
        </div>
      )}
      <button className="btn btn--primary" disabled={busy}>{mode === "all" ? "Показать все" : "Применить"}</button>
    </form>
  );
}

function MaintenancePanel({ onCleared }: { onCleared: () => void }) {
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function clear(which: "values" | "results") {
    const name = which === "values" ? "Values (исходные значения)" : "Results (результаты)";
    if (!confirm(`Удалить все записи из таблицы ${name} и сбросить счётчик Id?`)) return;
    try {
      const text = which === "values" ? await data.clearValues() : await data.clearResults();
      setMsg({ ok: true, text: `${name}: ${text}` });
      onCleared();
    } catch (e) {
      setMsg({ ok: false, text: errText(e) });
    }
  }

  return (
    <div className="panel panel--danger">
      <h3>Очистка таблиц</h3>
      <div className="row">
        <button className="btn btn--danger" onClick={() => clear("values")}>Очистить Values</button>
        <button className="btn btn--danger" onClick={() => clear("results")}>Очистить Results</button>
      </div>
      {msg && <p className={msg.ok ? "notice" : "error"} role="status">{msg.text}</p>}
    </div>
  );
}

function ResultsTable({ rows }: { rows: ResultRow[] | null }) {
  if (rows === null) return <p className="muted">Загрузка…</p>;
  if (rows.length === 0) return <p className="empty">Ничего не найдено. Загрузите CSV-файл или измените фильтр.</p>;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Id</th><th>Файл</th><th>Старт, UTC</th><th className="num">Длительность, с</th>
            <th className="num">Ср. время</th><th className="num">Ср. значение</th><th className="num">Медиана</th>
            <th className="num">Мин</th><th className="num">Макс</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td className="num">{r.id}</td><td>{r.fileName}</td><td>{fmtDate(r.startDate)}</td>
              <td className="num">{fmtNum(r.timeDeltaSec)}</td><td className="num">{fmtNum(r.avgExecutionTime)}</td>
              <td className="num">{fmtNum(r.avgValue)}</td><td className="num">{fmtNum(r.medianValue)}</td>
              <td className="num">{fmtNum(r.minValue)}</td><td className="num">{fmtNum(r.maxValue)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ValuesTable({ rows }: { rows: ValueRow[] }) {
  const files = [...new Set(rows.map((r) => r.fileName))];
  const [file, setFile] = useState("");
  const shown = file ? rows.filter((r) => r.fileName === file) : rows;
  if (rows.length === 0) return <p className="empty">Таблица Values пуста.</p>;
  return (
    <>
      <label className="field field--inline">
        <span className="field__label">Файл</span>
        <select value={file} onChange={(e) => setFile(e.target.value)}>
          <option value="">Все файлы ({rows.length})</option>
          {files.map((f) => <option key={f} value={f}>{f}</option>)}
        </select>
      </label>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr><th>Id</th><th>Дата, UTC</th><th className="num">Время выполнения</th><th className="num">Значение</th><th>Файл</th></tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.id}>
                <td className="num">{r.id}</td><td>{fmtDate(r.date)}</td>
                <td className="num">{fmtNum(r.executionTime)}</td><td className="num">{fmtNum(r.value)}</td><td>{r.fileName}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
