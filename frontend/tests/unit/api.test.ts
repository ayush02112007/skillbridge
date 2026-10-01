/**
 * API client contract.
 *
 * The client is the single place where the `{ success, data, meta }` envelope,
 * bearer tokens and 401 refresh are handled, so these behaviours are pinned
 * here rather than re-tested in every feature.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiError as ApiErrorInstance } from "@/lib/api";
import type { TokenPair } from "@/types/api";

type ApiModule = typeof import("@/lib/api");

/** Fresh module instance — the refresh single-flight promise is module state. */
async function loadApi(): Promise<ApiModule> {
  vi.resetModules();
  return import("@/lib/api");
}

/** A token pair shaped like the one `/auth/login` returns. */
function tokens(access: string, refresh: string): TokenPair {
  return {
    access_token: access,
    refresh_token: refresh,
    token_type: "bearer",
    expires_in: 1800,
    expires_at: new Date(Date.now() + 1800_000).toISOString(),
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  window.localStorage.clear();
});

describe("envelope handling", () => {
  it("unwraps `data` out of a success envelope", async () => {
    const { api } = await loadApi();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ success: true, data: { id: "s-1", name: "Ravi" } })),
    );

    await expect(api.get("/students/me")).resolves.toEqual({ id: "s-1", name: "Ravi" });
  });

  it("passes through a response that is not enveloped", async () => {
    const { api } = await loadApi();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "ok" })));

    await expect(api.get("/health")).resolves.toEqual({ status: "ok" });
  });

  it("keeps `meta` on paginated calls", async () => {
    const { api } = await loadApi();
    const page = { success: true, data: [{ id: 1 }], meta: { page: 2, total: 57, pages: 6 } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(page)));

    const result = await api.paged<{ id: number }>("/opportunities", { page: 2 });
    expect(result.meta.total).toBe(57);
    expect(result.data).toHaveLength(1);
  });

  it("returns undefined for 204 instead of failing to parse an empty body", async () => {
    const { api } = await loadApi();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));

    await expect(api.delete("/students/me/projects/p-1")).resolves.toBeUndefined();
  });
});

describe("URL building", () => {
  it("prefixes /api/v1 and serialises query parameters", async () => {
    const { api, API_BASE } = await loadApi();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: true, data: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await api.get("/opportunities", { type: "INTERNSHIP", page: 2, skills: ["react", "sql"] });

    const url = new URL(fetchMock.mock.calls[0][0] as string);
    expect(url.origin + url.pathname).toBe(`${API_BASE}/api/v1/opportunities`);
    expect(url.searchParams.get("type")).toBe("INTERNSHIP");
    expect(url.searchParams.getAll("skills")).toEqual(["react", "sql"]);
  });

  it("drops empty parameters so filters clear cleanly", async () => {
    const { api } = await loadApi();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: true, data: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await api.get("/opportunities", { search: "", location: null, mode: undefined, page: 1 });

    const url = new URL(fetchMock.mock.calls[0][0] as string);
    expect([...url.searchParams.keys()]).toEqual(["page"]);
  });

  it("does not double-prefix a path that already starts with /api", async () => {
    const { api, API_BASE } = await loadApi();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ status: "ok" }));
    vi.stubGlobal("fetch", fetchMock);

    await api.get("/api/v1/health");
    expect(fetchMock.mock.calls[0][0]).toBe(`${API_BASE}/api/v1/health`);
  });
});

describe("authentication headers", () => {
  it("attaches the bearer token when one is stored", async () => {
    const { api, tokenStore } = await loadApi();
    tokenStore.set(tokens("access-1", "refresh-1"));
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: true, data: {} }));
    vi.stubGlobal("fetch", fetchMock);

    await api.get("/students/me");

    const headers = (fetchMock.mock.calls[0][1] as RequestInit).headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer access-1");
  });

  it("omits the token on anonymous calls", async () => {
    const { api, tokenStore } = await loadApi();
    tokenStore.set(tokens("access-1", "refresh-1"));
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: true, data: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await api.get("/opportunities", undefined, { anonymous: true });

    const headers = (fetchMock.mock.calls[0][1] as RequestInit).headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it("lets the browser set the boundary for multipart uploads", async () => {
    const { api } = await loadApi();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: true, data: {} }));
    vi.stubGlobal("fetch", fetchMock);

    const form = new FormData();
    form.append("file", new Blob(["cv"], { type: "application/pdf" }), "cv.pdf");
    await api.post("/documents", form);

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>)["Content-Type"]).toBeUndefined();
    expect(init.body).toBeInstanceOf(FormData);
  });
});

describe("error mapping", () => {
  it("turns an error envelope into a typed ApiError", async () => {
    const { api, ApiError } = await loadApi();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          { success: false, error: { code: "ALREADY_APPLIED", message: "You have already applied." } },
          409,
        ),
      ),
    );

    const error = await api.post<never>("/applications", {}).catch((e: unknown) => e as ApiErrorInstance);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(409);
    expect(error.code).toBe("ALREADY_APPLIED");
    expect(error.message).toBe("You have already applied.");
  });

  it("exposes field errors for form binding", async () => {
    const { api } = await loadApi();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            success: false,
            error: {
              code: "VALIDATION_ERROR",
              message: "Invalid input",
              details: {
                fields: [
                  { field: "email", message: "Email already registered" },
                  { field: "password", message: "Password is too common" },
                ],
              },
            },
          },
          422,
        ),
      ),
    );

    const error = await api.post<never>("/auth/register", {}).catch((e: unknown) => e as ApiErrorInstance);
    expect(error.fieldErrors).toEqual({
      email: "Email already registered",
      password: "Password is too common",
    });
  });

  it("survives a non-JSON error from a proxy", async () => {
    const { api, ApiError } = await loadApi();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("<html>502 Bad Gateway</html>", { status: 502 })),
    );

    const error = await api.get<never>("/students/me").catch((e: unknown) => e as ApiErrorInstance);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(502);
    expect(error.code).toBe("REQUEST_FAILED");
  });
});

describe("token refresh", () => {
  it("refreshes once on a 401 and replays the original request", async () => {
    const { api, tokenStore } = await loadApi();
    tokenStore.set(tokens("stale", "refresh-1"));

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ success: false, error: { code: "TOKEN_EXPIRED", message: "expired" } }, 401),
      )
      .mockResolvedValueOnce(
        jsonResponse({ success: true, data: tokens("fresh", "refresh-2") }),
      )
      .mockResolvedValueOnce(jsonResponse({ success: true, data: { id: "s-1" } }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.get("/students/me")).resolves.toEqual({ id: "s-1" });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls[1][0])).toContain("/auth/refresh");
    // The replay carries the new token, and rotation has been persisted.
    const replayHeaders = (fetchMock.mock.calls[2][1] as RequestInit).headers as Record<string, string>;
    expect(replayHeaders.Authorization).toBe("Bearer fresh");
    expect(tokenStore.access).toBe("fresh");
    expect(tokenStore.refresh).toBe("refresh-2");
  });

  it("collapses concurrent 401s into a single refresh call", async () => {
    const { api, tokenStore } = await loadApi();
    tokenStore.set(tokens("stale", "refresh-1"));

    let refreshCalls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/auth/refresh")) {
          refreshCalls += 1;
          // A real round-trip leaves a window in which a second, racing
          // refresh could rotate the token again and revoke this one.
          await new Promise((resolve) => setTimeout(resolve, 10));
          return jsonResponse({
            success: true,
            data: tokens("fresh", "refresh-2"),
          });
        }
        const auth = (init?.headers as Record<string, string> | undefined)?.Authorization;
        if (auth === "Bearer fresh") return jsonResponse({ success: true, data: { ok: true } });
        return jsonResponse({ success: false, error: { code: "TOKEN_EXPIRED", message: "expired" } }, 401);
      }),
    );


    const results = await Promise.all([
      api.get("/students/me"),
      api.get("/notifications"),
      api.get("/applications"),
    ]);

    expect(results).toEqual([{ ok: true }, { ok: true }, { ok: true }]);
    expect(refreshCalls).toBe(1);
  });

  it("clears the session when the refresh token is rejected", async () => {
    const { api, tokenStore } = await loadApi();
    tokenStore.set(tokens("stale", "revoked"));

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) =>
        String(input).includes("/auth/refresh")
          ? jsonResponse({ success: false, error: { code: "TOKEN_REUSED", message: "revoked" } }, 401)
          : jsonResponse({ success: false, error: { code: "TOKEN_EXPIRED", message: "expired" } }, 401),
      ),
    );

    const error = await api.get<never>("/students/me").catch((e: unknown) => e as ApiErrorInstance);
    expect(error.status).toBe(401);
    expect(tokenStore.access).toBeNull();
    expect(tokenStore.refresh).toBeNull();
  });

  it("does not attempt a refresh when there is no refresh token", async () => {
    const { api } = await loadApi();
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        jsonResponse({ success: false, error: { code: "NOT_AUTHENTICATED", message: "no token" } }, 401),
      );
    vi.stubGlobal("fetch", fetchMock);

    await api.get("/students/me").catch(() => undefined);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("tokenStore", () => {
  it("round-trips and clears tokens", async () => {
    const { tokenStore } = await loadApi();
    expect(tokenStore.access).toBeNull();

    tokenStore.set(tokens("a", "r"));
    expect(tokenStore.access).toBe("a");
    expect(tokenStore.refresh).toBe("r");

    tokenStore.clear();
    expect(tokenStore.access).toBeNull();
    expect(tokenStore.refresh).toBeNull();
  });
});
