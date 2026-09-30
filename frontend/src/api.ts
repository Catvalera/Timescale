// Клиент для двух микросервисов, доступных через один origin (vite proxy / nginx):
//   /api/auth -> auth-service,  /api/data -> timescale-service
const AUTH = "/api/auth";
const DATA = "/api/data";
const ACCESS_HEADER = "X-Access-Token";
const REFRESH_HEADER = "X-Refresh-Token";

export type Purpose = "registration" | "login";

export interface User {
  id: number;
  full_name: string;
  email: string;
  nickname: string;
  is_verified: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface PendingVerification {
  token: string;
  purpose: Purpose;
  email: string;
  resendAfter: number;
  sentAt: number;
}

export interface ResultRow {
  id: number;
  fileName: string;
  timeDeltaSec: number;
  startDate: string;
  avgExecutionTime: number;
  avgValue: number;
  medianValue: number;
  maxValue: number;
  minValue: number;
}

export interface ValueRow {
  id: number;
  date: string;
  executionTime: number;
  value: number;
  fileName: string;
}

interface ResultData<T = unknown> {
  status: "success" | "error";
  data?: T;
  token?: { access_token: string; refresh_token: string } | null;
  error?: { code: number; log: string } | null;
}

export class ApiError extends Error {
  constructor(message: string, public status: number, public code?: number) {
    super(message);
  }
}

// ---------- хранение токенов ----------
const store = {
  get access() { return localStorage.getItem("access_token"); },
  get refresh() { return localStorage.getItem("refresh_token"); },
  setPair(access: string, refresh: string) {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
  },
  clear() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
  },
};

export const session = {
  hasTokens: () => Boolean(store.access && store.refresh),
  user(): User | null {
    try { return JSON.parse(localStorage.getItem("user") ?? "null"); } catch { return null; }
  },
  setUser(user: User) { localStorage.setItem("user", JSON.stringify(user)); },
  clear: () => store.clear(),
  pending(): PendingVerification | null {
    try { return JSON.parse(sessionStorage.getItem("pending_verification") ?? "null"); } catch { return null; }
  },
  setPending(p: PendingVerification | null) {
    if (p) sessionStorage.setItem("pending_verification", JSON.stringify(p));
    else sessionStorage.removeItem("pending_verification");
  },
};

let onSessionExpired: () => void = () => {};
export function setSessionExpiredHandler(fn: () => void) { onSessionExpired = fn; }

// ---------- разбор ответов ----------
async function readError(res: Response): Promise<ApiError> {
  const text = await res.text();
  try {
    const body = JSON.parse(text);
    if (body?.error?.log) return new ApiError(body.error.log, res.status, body.error.code);   // auth-service
    if (typeof body?.detail === "string") return new ApiError(body.detail, res.status);        // timescale-service
    if (Array.isArray(body?.detail)) return new ApiError(body.detail.map((d: { msg: string }) => d.msg).join("; "), res.status);
  } catch { /* не JSON — например, текст ошибки загрузки файла */ }
  return new ApiError(text || `Ошибка ${res.status}`, res.status);
}

async function authCall<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<ResultData<T>> {
  const headers = new Headers(init.headers);
  if (init.json !== undefined) headers.set("Content-Type", "application/json");
  let res: Response;
  try {
    res = await fetch(AUTH + path, { ...init, headers, body: init.json !== undefined ? JSON.stringify(init.json) : init.body });
  } catch {
    throw new ApiError("Сервис авторизации недоступен", 0);
  }
  if (!res.ok) throw await readError(res);
  return res.json();
}

// ---------- авторизация ----------
interface VerificationData { requires_verification: true; purpose: Purpose; email: string; resend_after: number; expires_in: number }
interface AuthorizedData { requires_verification: false; user: User }

function toPending(r: ResultData<VerificationData>): PendingVerification {
  return {
    token: r.token!.access_token, purpose: r.data!.purpose, email: r.data!.email,
    resendAfter: r.data!.resend_after, sentAt: Date.now(),
  };
}

export const auth = {
  async register(body: { full_name: string; email: string; nickname: string; password: string }) {
    return toPending(await authCall<VerificationData>("/registration", { method: "POST", json: body }));
  },
  async login(email: string, password: string) {
    return toPending(await authCall<VerificationData>("/login", { method: "POST", json: { email, password } }));
  },
  async verify(pending: PendingVerification, code: string) {
    const r = await authCall<AuthorizedData>("/verify", {
      method: "POST", json: { code }, headers: { [ACCESS_HEADER]: pending.token },
    });
    store.setPair(r.token!.access_token, r.token!.refresh_token);
    session.setUser(r.data!.user);
    session.setPending(null);
    return r.data!.user;
  },
  async resend(pending: PendingVerification) {
    return toPending(await authCall<VerificationData>("/verify/resend", {
      method: "POST", headers: { [ACCESS_HEADER]: pending.token },
    }));
  },
  async logout() {
    const access = store.access;
    store.clear();
    if (access) {
      await authCall("/logout", { method: "POST", headers: { [ACCESS_HEADER]: access } }).catch(() => undefined);
    }
  },
};

let refreshing: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const refresh = store.refresh;
  if (!refresh) return false;
  refreshing ??= authCall("/tokens/refresh", { method: "POST", headers: { [REFRESH_HEADER]: refresh } })
    .then((r) => { store.setPair(r.token!.access_token, r.token!.refresh_token); return true; })
    .catch(() => false)
    .finally(() => { refreshing = null; });
  return refreshing;
}

// ---------- API данных (timescale-service) ----------
async function dataCall(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const headers = new Headers(init.headers);
  if (store.access) headers.set(ACCESS_HEADER, store.access);
  let res: Response;
  try {
    res = await fetch(DATA + path, { ...init, headers });
  } catch {
    throw new ApiError("Сервис данных недоступен", 0);
  }
  if (res.status === 401 && retry && (await refreshTokens())) return dataCall(path, init, false);
  if (res.status === 401) {
    store.clear();
    onSessionExpired();
    throw new ApiError("Сессия истекла. Войдите снова", 401);
  }
  if (!res.ok) throw await readError(res);
  return res;
}

const q = (params: Record<string, string | number>) => "?" + new URLSearchParams(
  Object.entries(params).map(([k, v]) => [k, String(v)])).toString();

export const data = {
  async upload(file: File): Promise<string> {
    const form = new FormData();
    form.append("file", file);
    return (await dataCall("/Upload_file", { method: "POST", body: form })).text();
  },
  results: async (): Promise<ResultRow[]> => (await dataCall("/Get_data_from_table_Result")).json(),
  values: async (): Promise<ValueRow[]> => (await dataCall("/Get_data_from_table_Value")).json(),
  byFileName: async (name: string): Promise<ResultRow[]> => (await dataCall("/Sort_by_filename" + q({ name }))).json(),
  byStartDate: async (startdate: string, enddate: string): Promise<ResultRow[]> =>
    (await dataCall("/Sort_by_StartDate" + q({ startdate, enddate }))).json(),
  byAvgValue: async (startValue: number, endValue: number): Promise<ResultRow[]> =>
    (await dataCall("/Sort_by_avg-Value" + q({ startValue, endValue }))).json(),
  byAvgExecutionTime: async (startValue: number, endValue: number): Promise<ResultRow[]> =>
    (await dataCall("/Sort_by_avg-ExecutionTime" + q({ startValue, endValue }))).json(),
  lastTen: async (Full_filename: string): Promise<ResultRow[]> =>
    (await dataCall("/Get_last_10_values_filter_from_filename" + q({ Full_filename }))).json(),
  clearValues: async () => (await dataCall("/api/Table_actions/clear_table_Value", { method: "DELETE" })).text(),
  clearResults: async () => (await dataCall("/api/Table_actions/clear_table_Result", { method: "DELETE" })).text(),
};
