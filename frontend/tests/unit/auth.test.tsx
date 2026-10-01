/**
 * Session context and the route guard.
 *
 * `can()` decides what the UI offers. It is presentation only — the API is
 * still the authority — but getting it wrong either hides work a user is
 * entitled to do, or dangles buttons that will be refused.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth, useRequireAuth } from "@/lib/auth";
import { tokenStore } from "@/lib/api";
import type { RoleName, SessionPayload, TokenPair } from "@/types/api";

const replace = vi.fn();
const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push, prefetch: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/student/dashboard",
}));

function tokens(): TokenPair {
  return {
    access_token: "access-1",
    refresh_token: "refresh-1",
    token_type: "bearer",
    expires_in: 1800,
    expires_at: new Date(Date.now() + 1800_000).toISOString(),
  };
}

function session(
  roles: RoleName[],
  permissions: string[],
  home = "/student/dashboard",
): SessionPayload {
  return {
    user: {
      id: "u-1",
      email: "student@demo.com",
      full_name: "Ravi Menon",
      avatar_url: null,
      status: "ACTIVE",
      is_email_verified: true,
      roles: roles.map((name) => ({ name, label: name })),
      created_at: new Date().toISOString(),
    },
    roles,
    permissions,
    home_route: home,
  } as unknown as SessionPayload;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function Probe() {
  const auth = useAuth();
  if (auth.isLoading) return <p>loading</p>;
  return (
    <div>
      <p data-testid="who">{auth.session?.user.full_name ?? "anonymous"}</p>
      <p data-testid="authenticated">{String(auth.isAuthenticated)}</p>
      <p data-testid="can-apply">{String(auth.can("application:create"))}</p>
      <p data-testid="can-both">
        {String(auth.can("application:create", "opportunity:create"))}
      </p>
      <p data-testid="is-student">{String(auth.hasRole("STUDENT"))}</p>
      <button type="button" onClick={() => void auth.logout()}>
        Sign out
      </button>
    </div>
  );
}

beforeEach(() => {
  replace.mockClear();
  push.mockClear();
  window.localStorage.clear();
});

describe("AuthProvider", () => {
  it("stays anonymous when there is no stored token, without calling the API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("who")).toHaveTextContent("anonymous"));
    expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("restores the session from a stored token", async () => {
    tokenStore.set(tokens());
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ success: true, data: session(["STUDENT"], ["application:create"]) }),
      ),
    );

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("who")).toHaveTextContent("Ravi Menon"));
    expect(screen.getByTestId("is-student")).toHaveTextContent("true");
  });

  it("discards a token the API rejects rather than looping on it", async () => {
    tokenStore.set(tokens());
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ success: false, error: { code: "TOKEN_EXPIRED", message: "expired" } }, 401),
      ),
    );

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("who")).toHaveTextContent("anonymous"));
    expect(tokenStore.access).toBeNull();
  });

  it("clears the local session even when the logout call fails", async () => {
    tokenStore.set(tokens());
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) =>
        String(input).includes("/auth/logout")
          ? Promise.reject(new Error("network down"))
          : jsonResponse({ success: true, data: session(["STUDENT"], []) }),
      ),
    );

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("who")).toHaveTextContent("Ravi Menon"));

    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => expect(tokenStore.access).toBeNull());
    expect(push).toHaveBeenCalledWith("/login");
  });
});

describe("can()", () => {
  async function renderWith(roles: RoleName[], permissions: string[]) {
    tokenStore.set(tokens());
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ success: true, data: session(roles, permissions) })),
    );
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.queryByText("loading")).not.toBeInTheDocument());
  }

  it("is false for everything when signed out", async () => {
    vi.stubGlobal("fetch", vi.fn());
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("can-apply")).toHaveTextContent("false"));
  });

  it("grants only the permissions the session carries", async () => {
    await renderWith(["STUDENT"], ["application:create"]);
    expect(screen.getByTestId("can-apply")).toHaveTextContent("true");
  });

  it("requires every permission asked for, not any of them", async () => {
    await renderWith(["STUDENT"], ["application:create"]);
    expect(screen.getByTestId("can-both")).toHaveTextContent("false");
  });

  it("lets a super admin through without enumerating permissions", async () => {
    await renderWith(["SUPER_ADMIN"], []);
    expect(screen.getByTestId("can-both")).toHaveTextContent("true");
  });
});

describe("useRequireAuth", () => {
  function Guarded({ allowed }: { allowed?: RoleName[] }) {
    const { session } = useRequireAuth(allowed);
    return <p data-testid="guarded">{session ? "visible" : "redirecting"}</p>;
  }

  it("sends an anonymous visitor to the sign-in page, keeping the destination", async () => {
    vi.stubGlobal("fetch", vi.fn());
    render(
      <AuthProvider>
        <Guarded />
      </AuthProvider>,
    );

    await waitFor(() => expect(replace).toHaveBeenCalled());
    expect(replace.mock.calls[0][0]).toContain("/login?next=");
  });

  it("sends a signed-in user without the role back to their own portal", async () => {
    tokenStore.set(tokens());
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ success: true, data: session(["STUDENT"], []) }),
      ),
    );

    render(
      <AuthProvider>
        <Guarded allowed={["INDUSTRY_ADMIN"]} />
      </AuthProvider>,
    );

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/student/dashboard"));
  });

  it("leaves an authorised user alone", async () => {
    tokenStore.set(tokens());
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ success: true, data: session(["STUDENT"], []) }),
      ),
    );

    render(
      <AuthProvider>
        <Guarded allowed={["STUDENT"]} />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("guarded")).toHaveTextContent("visible"));
    expect(replace).not.toHaveBeenCalled();
  });
});

describe("useAuth outside a provider", () => {
  it("fails loudly instead of returning an empty session", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Probe />)).toThrow(/useAuth must be used inside/);
    spy.mockRestore();
  });
});
