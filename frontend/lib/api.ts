// Typed API client for the GraphIntel FastAPI backend.
// Single fetch wrapper; reads NEXT_PUBLIC_API_BASE.

import type {
  AdminStats,
  AnswerOut,
  AuditEntry,
  ChunkOut,
  DocumentOut,
  EntityOut,
  EvalRunOut,
  GraphView,
  HealthOut,
  JobOut,
  ReadyOut,
  RelationOut,
  ReleaseGate,
  SeedResult,
} from "./types";

export const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"
).replace(/\/+$/, "");

/** Error carrying the HTTP status and any parsed body from the backend. */
export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export type QueryValue = string | number | boolean | undefined | null;
export type QueryParams = Record<string, QueryValue | QueryValue[]>;

/** Build a full URL with query params. Array values repeat the key. */
export function buildUrl(path: string, params?: QueryParams): string {
  const base = path.startsWith("http")
    ? path
    : `${API_BASE}${path.startsWith("/") ? "" : "/"}${path}`;
  if (!params) return base;

  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item === undefined || item === null) continue;
        search.append(key, String(item));
      }
    } else {
      search.append(key, String(value));
    }
  }
  const qs = search.toString();
  return qs ? `${base}?${qs}` : base;
}

interface RequestOptions {
  method?: string;
  params?: QueryParams;
  body?: unknown;
  formData?: FormData;
  signal?: AbortSignal;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", params, body, formData, signal } = opts;
  const url = buildUrl(path, params);

  const headers: Record<string, string> = {};
  let payload: BodyInit | undefined;

  if (formData) {
    payload = formData;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let res: Response;
  try {
    res = await fetch(url, { method, headers, body: payload, signal });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError(
      `Network error contacting backend at ${API_BASE}. Is it running?`,
      0,
      err,
    );
  }

  const text = await res.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (!res.ok) {
    const detail =
      (parsed && typeof parsed === "object" && "detail" in parsed
        ? (parsed as { detail: unknown }).detail
        : undefined) ?? res.statusText;
    const message =
      typeof detail === "string" ? detail : JSON.stringify(detail);
    throw new ApiError(message || `Request failed (${res.status})`, res.status, parsed);
  }

  return parsed as T;
}

export const api = {
  // ---- Meta ----
  health: () => request<HealthOut>("/health"),
  ready: () => request<ReadyOut>("/ready"),

  // ---- Admin / stats ----
  seed: (reset = true) =>
    request<SeedResult>("/admin/seed", { method: "POST", params: { reset } }),
  stats: (signal?: AbortSignal) =>
    request<AdminStats>("/admin/stats", { signal }),
  audits: (params?: { action?: string; limit?: number }, signal?: AbortSignal) =>
    request<AuditEntry[]>("/audits", { params, signal }),

  // ---- Ingestion & jobs ----
  uploadFile: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<JobOut>("/ingest/upload", { method: "POST", formData: fd });
  },
  ingestText: (input: {
    filename: string;
    content: string;
    source_kind?: string;
  }) => request<JobOut>("/ingest/text", { method: "POST", body: input }),
  jobs: (
    params?: { state?: string; limit?: number },
    signal?: AbortSignal,
  ) => request<JobOut[]>("/jobs", { params, signal }),
  job: (id: string, signal?: AbortSignal) =>
    request<JobOut>(`/jobs/${encodeURIComponent(id)}`, { signal }),
  documents: (
    params?: { source_kind?: string; limit?: number },
    signal?: AbortSignal,
  ) => request<DocumentOut[]>("/documents", { params, signal }),
  documentChunks: (id: string, signal?: AbortSignal) =>
    request<ChunkOut[]>(`/documents/${encodeURIComponent(id)}/chunks`, {
      signal,
    }),

  // ---- Entities & relations ----
  entities: (
    params?: {
      type?: string;
      q?: string;
      include_merged?: boolean;
      limit?: number;
    },
    signal?: AbortSignal,
  ) => request<EntityOut[]>("/entities", { params, signal }),
  entity: (id: string, signal?: AbortSignal) =>
    request<EntityOut>(`/entities/${encodeURIComponent(id)}`, { signal }),
  patchEntity: (
    id: string,
    body: {
      canonical_name?: string;
      aliases?: string[];
      attributes?: Record<string, unknown>;
      actor?: string;
    },
  ) =>
    request<EntityOut>(`/entities/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body,
    }),
  mergeEntities: (body: {
    source_id: string;
    target_id: string;
    actor?: string;
  }) =>
    request<{ merged: string; target: EntityOut }>("/entities/merge", {
      method: "POST",
      body,
    }),
  relations: (
    params?: {
      type?: string;
      entity?: string;
      include_deleted?: boolean;
      limit?: number;
    },
    signal?: AbortSignal,
  ) => request<RelationOut[]>("/relations", { params, signal }),
  createRelation: (body: {
    type: string;
    source_id: string;
    target_id: string;
    confidence?: number;
    actor?: string;
  }) => request<RelationOut>("/relations", { method: "POST", body }),
  deleteRelation: (id: string, body?: { reason?: string; actor?: string }) =>
    request<{ deleted: string }>(`/relations/${encodeURIComponent(id)}`, {
      method: "DELETE",
      body: body ?? {},
    }),

  // ---- Graph ----
  graph: (
    params?: { types?: string; rel_types?: string; limit?: number },
    signal?: AbortSignal,
  ) => request<GraphView>("/graph", { params, signal }),
  graphExpand: (
    params: { seed: string[]; hops?: number; rel_types?: string },
    signal?: AbortSignal,
  ) => request<GraphView>("/graph/expand", { params, signal }),

  // ---- Ask ----
  ask: (body: { question: string; top_k?: number; as_of?: string }) =>
    request<AnswerOut>("/ask", { method: "POST", body }),
  answer: (id: string, signal?: AbortSignal) =>
    request<AnswerOut>(`/answers/${encodeURIComponent(id)}`, { signal }),

  // ---- Evaluation ----
  evalRun: () => request<EvalRunOut>("/eval/run", { method: "POST" }),
  evalLatest: (signal?: AbortSignal) =>
    request<EvalRunOut>("/eval/latest", { signal }),
  releaseGate: (signal?: AbortSignal) =>
    request<ReleaseGate>("/eval/release-gate", { signal }),
};
