import { getToken } from "./auth";
import type {
  Account, Alert, AuthUser, GeoPoint, IngestionRun, KPIs, LanguageBreakdown,
  Mention, MentionListResponse, SourceBreakdown, TopicCluster, Tracker,
  TrendPoint, CrossChannelInsight, EmotionStat, AuthorStat, VelocityData,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20_000);

  try {
    const res = await fetch(`${BASE}${path}`, { ...options, headers, signal: controller.signal });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail ?? "Request failed");
    }
    if (res.status === 204) return undefined as T;
    return res.json();
  } finally {
    clearTimeout(timer);
  }
}

// ── Auth ────────────────────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user_id: string; account_id: string; account_name: string; account_slug: string; role: string }>(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) }
    ),
  me: () => request<AuthUser>("/auth/me"),
};

// ── Account ─────────────────────────────────────────────────────────────────

export const accountApi = {
  get: () => request<Account>("/account"),
  update: (data: Partial<Account> & { agent_api_token?: string }) =>
    request<Account>("/account", { method: "PUT", body: JSON.stringify(data) }),
};

// ── Trackers ─────────────────────────────────────────────────────────────────

export const trackersApi = {
  list: () => request<Tracker[]>("/trackers"),
  get: (id: string) => request<Tracker>(`/trackers/${id}`),
  create: (data: Partial<Tracker>) =>
    request<Tracker>("/trackers", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Tracker>) =>
    request<Tracker>(`/trackers/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    request<void>(`/trackers/${id}`, { method: "DELETE" }),
  refresh: (id: string) =>
    request<{ status: string }>(`/trackers/${id}/refresh`, { method: "POST" }),
};

// ── Mentions ──────────────────────────────────────────────────────────────────

export const mentionsApi = {
  list: (params: Record<string, string | number | boolean | undefined>) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== "") q.set(k, String(v));
    }
    return request<MentionListResponse>(`/mentions?${q}`);
  },
  get: (id: string) => request<Mention>(`/mentions/${id}`),
  triage: (id: string, data: { triage_status?: string; triage_priority?: string; triage_assignee?: string; triage_note?: string }) =>
    request<Mention>(`/mentions/${id}/triage`, { method: "PATCH", body: JSON.stringify(data) }),
  draftReply: (id: string) =>
    request<{ draft_reply: string | null }>(`/mentions/${id}/draft-reply`, { method: "POST" }),
};

// ── Analytics ─────────────────────────────────────────────────────────────────

export const analyticsApi = {
  kpis: (params?: { tracker_id?: string; days?: number }) =>
    request<KPIs>(`/analytics/kpis${_qs(params)}`),
  trends: (params?: { tracker_id?: string; days?: number; granularity?: string }) =>
    request<TrendPoint[]>(`/analytics/trends${_qs(params)}`),
  geographic: (params?: { tracker_id?: string; days?: number }) =>
    request<GeoPoint[]>(`/analytics/geographic${_qs(params)}`),
  sources: (params?: { tracker_id?: string; days?: number }) =>
    request<SourceBreakdown[]>(`/analytics/sources${_qs(params)}`),
  authors: (params?: { tracker_id?: string; days?: number }) =>
    request<AuthorStat[]>(`/analytics/authors${_qs(params)}`),
  languages: (params?: { tracker_id?: string; days?: number }) =>
    request<LanguageBreakdown[]>(`/analytics/languages${_qs(params)}`),
  emotions: (params?: { tracker_id?: string; days?: number }) =>
    request<EmotionStat[]>(`/analytics/emotions${_qs(params)}`),
  calendar: (params?: { tracker_id?: string }) =>
    request<{ date: string; total: number; negative_share: number }[]>(`/analytics/calendar${_qs(params)}`),
  velocity: (params?: { tracker_id?: string }) =>
    request<VelocityData>(`/analytics/velocity${_qs(params)}`),
};

// ── Alerts ────────────────────────────────────────────────────────────────────

export const alertsApi = {
  list: (params?: { tracker_id?: string; severity?: string; is_resolved?: boolean }) =>
    request<Alert[]>(`/alerts${_qs(params)}`),
  get: (id: string) => request<Alert>(`/alerts/${id}`),
  resolve: (id: string) =>
    request<Alert>(`/alerts/${id}/resolve`, { method: "PATCH" }),
  draftResponse: (id: string) =>
    request<{ draft_response: string | null }>(`/alerts/${id}/draft-response`, { method: "POST" }),
};

// ── Topics ────────────────────────────────────────────────────────────────────

export const topicsApi = {
  list: (params?: { tracker_id?: string }) =>
    request<TopicCluster[]>(`/topics${_qs(params)}`),
  recluster: (tracker_id?: string) =>
    request<{ status: string }>(`/topics/recluster${tracker_id ? `?tracker_id=${tracker_id}` : ""}`, { method: "POST" }),
  mentions: (id: string, page = 1) =>
    request<Mention[]>(`/topics/${id}/mentions?page=${page}`),
};

// ── Insights ──────────────────────────────────────────────────────────────────

export const insightsApi = {
  list: () => request<CrossChannelInsight[]>("/insights"),
  generate: () => request<{ status: string }>("/insights/generate", { method: "POST" }),
};

// ── Saved Filters ─────────────────────────────────────────────────────────────

export interface SavedFilter {
  id: string;
  name: string;
  tracker_id?: string | null;
  filter_params: Record<string, string | number | boolean>;
  created_by?: string | null;
}

export const filtersApi = {
  list: () => request<SavedFilter[]>("/filters"),
  create: (data: { name: string; tracker_id?: string; filter_params: Record<string, string | number | boolean> }) =>
    request<SavedFilter>("/filters", { method: "POST", body: JSON.stringify(data) }),
  delete: (id: string) => request<void>(`/filters/${id}`, { method: "DELETE" }),
};

// ── Ingestion ─────────────────────────────────────────────────────────────────

export const ingestApi = {
  runs: (tracker_id?: string) =>
    request<IngestionRun[]>(`/ingest/runs${tracker_id ? `?tracker_id=${tracker_id}` : ""}`),
};

// ── Export ────────────────────────────────────────────────────────────────────

export const exportApi = {
  mentionsCsvUrl: (params?: {
    tracker_id?: string; days?: number; token?: string;
    sentiment?: string; source?: string; search?: string;
    language?: string; region?: string; date_from?: string; date_to?: string;
  }) => `${BASE}/export/mentions.csv${_qs(params)}`,
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function _qs(params?: Record<string, string | number | boolean | undefined>): string {
  if (!params) return "";
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) q.set(k, String(v));
  }
  const str = q.toString();
  return str ? `?${str}` : "";
}
