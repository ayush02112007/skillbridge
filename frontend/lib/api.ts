/**
 * Typed API client.
 *
 * Responsibilities kept deliberately in one place:
 *  - attaches the bearer token,
 *  - refreshes it exactly once on a 401 and replays the request,
 *  - unwraps the `{ success, data }` envelope,
 *  - converts API error envelopes into a typed `ApiError`.
 */
import type { ApiErrorBody, Envelope, Paged, TokenPair } from "@/types/api";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";
export const API_PREFIX = "/api/v1";

const ACCESS_KEY = "sb.access_token";
const REFRESH_KEY = "sb.refresh_token";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  /** Field-level messages from a validation error, keyed by field path. */
  get fieldErrors(): Record<string, string> {
    const out: Record<string, string> = {};
    const details = this.details as { fields?: { field: string; message: string }[] };
    for (const entry of details?.fields ?? []) out[entry.field] = entry.message;
    return out;
  }
}

// ----------------------------------------------------------------- tokens --
export const tokenStore = {
  get access(): string | null {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(ACCESS_KEY);
  },
  get refresh(): string | null {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(REFRESH_KEY);
  },
  set(tokens: TokenPair) {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(ACCESS_KEY, tokens.access_token);
    window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  },
  clear() {
    if (typeof window === "undefined") return;
    window.localStorage.removeItem(ACCESS_KEY);
    window.localStorage.removeItem(REFRESH_KEY);
  },
};

let refreshInFlight: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;

  // Collapse concurrent 401s into a single refresh call; a second rotation
  // would invalidate the first and log the user out.
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const response = await fetch(`${API_BASE}${API_PREFIX}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!response.ok) {
          tokenStore.clear();
          return false;
        }
        const body = (await response.json()) as Envelope<TokenPair>;
        tokenStore.set(body.data);
        return true;
      } catch {
        tokenStore.clear();
        return false;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  query?: Record<string, unknown>;
  /** Skip the auth header (used for public endpoints). */
  anonymous?: boolean;
  /** Return the raw Response instead of unwrapping (file downloads). */
  raw?: boolean;
}

function buildUrl(path: string, query?: Record<string, unknown>): string {
  const url = new URL(
    `${API_BASE}${path.startsWith("/api") ? "" : API_PREFIX}${path}`,
  );
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      value.forEach((v) => v !== undefined && url.searchParams.append(key, String(v)));
    } else {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function toApiError(response: Response): Promise<ApiError> {
  let code = "REQUEST_FAILED";
  let message = response.statusText || "Request failed";
  let details: unknown;
  try {
    const body = (await response.json()) as ApiErrorBody;
    if (body?.error) {
      code = body.error.code;
      message = body.error.message;
      details = body.error.details;
    }
  } catch {
    // Non-JSON error (proxy, network appliance): keep the status text.
  }
  return new ApiError(response.status, code, message, details);
}

async function send(path: string, options: RequestOptions, retry = true): Promise<Response> {
  // `raw` is consumed by apiRequest, not by fetch, so it is destructured out.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { body, query, anonymous, raw: _raw, headers, ...rest } = options;
  const token = anonymous ? null : tokenStore.access;

  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
  const response = await fetch(buildUrl(path, query), {
    ...rest,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(headers as Record<string, string>),
    },
    body: isFormData ? (body as FormData) : body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401 && retry && !anonymous && tokenStore.refresh) {
    if (await refreshTokens()) return send(path, options, false);
  }
  return response;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await send(path, options);
  if (!response.ok) throw await toApiError(response);
  if (options.raw) return response as unknown as T;
  if (response.status === 204) return undefined as T;

  const body = await response.json();
  // Unwrap the envelope; paginated responses keep `meta` alongside `data`.
  if (body && typeof body === "object" && "success" in body && "data" in body) {
    return (body as Envelope<T>).data;
  }
  return body as T;
}

/** Paginated GET that preserves `meta`. */
export async function apiPaged<T>(
  path: string,
  query?: Record<string, unknown>,
): Promise<Paged<T>> {
  const response = await send(path, { method: "GET", query });
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as Paged<T>;
}

export const api = {
  get: <T>(path: string, query?: Record<string, unknown>, options?: RequestOptions) =>
    apiRequest<T>(path, { ...options, method: "GET", query }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(path, { ...options, method: "POST", body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(path, { ...options, method: "PUT", body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(path, { ...options, method: "PATCH", body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    apiRequest<T>(path, { ...options, method: "DELETE" }),
  paged: apiPaged,
};

/** Download a file (PDF/CSV) and hand it to the browser. */
export async function downloadFile(path: string, filename: string, query?: Record<string, unknown>) {
  const response = await send(path, { method: "GET", query, raw: true });
  if (!response.ok) throw await toApiError(response);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
