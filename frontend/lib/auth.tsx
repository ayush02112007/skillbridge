"use client";

/**
 * Authentication context.
 *
 * Holds the session returned by the API (user, roles, permissions, landing
 * route) and exposes `can()` so the UI hides what the API would refuse. The
 * server remains the authority: this is presentation, not enforcement.
 */
import { useRouter } from "next/navigation";
import {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
} from "react";

import { api, ApiError, tokenStore } from "@/lib/api";
import type { AuthResponse, RoleName, SessionPayload } from "@/types/api";

interface AuthContextValue {
  session: SessionPayload | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  roles: RoleName[];
  login: (email: string, password: string) => Promise<SessionPayload>;
  register: (payload: RegisterPayload) => Promise<SessionPayload>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  can: (...permissions: string[]) => boolean;
  hasRole: (...roles: RoleName[]) => boolean;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  role: "STUDENT" | "ACADEMICIAN" | "INDUSTRY_RECRUITER" | "INDUSTRY_ADMIN";
  phone?: string;
  institution_id?: string;
  company_id?: string;
  company_name?: string;
  accept_terms: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [isLoading, setLoading] = useState(true);
  const router = useRouter();

  const loadSession = useCallback(async () => {
    if (!tokenStore.access) {
      setSession(null);
      setLoading(false);
      return;
    }
    try {
      setSession(await api.get<SessionPayload>("/auth/me"));
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) tokenStore.clear();
      setSession(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  const login = useCallback(async (email: string, password: string) => {
    const result = await api.post<AuthResponse>(
      "/auth/login",
      { email, password },
      { anonymous: true },
    );
    tokenStore.set(result.tokens);
    setSession(result.session);
    return result.session;
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    const result = await api.post<AuthResponse>("/auth/register", payload, {
      anonymous: true,
    });
    tokenStore.set(result.tokens);
    setSession(result.session);
    return result.session;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout", { refresh_token: tokenStore.refresh });
    } catch {
      // Signing out locally must succeed even if the API call does not.
    }
    tokenStore.clear();
    setSession(null);
    router.push("/login");
  }, [router]);

  const can = useCallback(
    (...permissions: string[]) => {
      if (!session) return false;
      if (session.roles.includes("SUPER_ADMIN")) return true;
      return permissions.every((p) => session.permissions.includes(p));
    },
    [session],
  );

  const hasRole = useCallback(
    (...roles: RoleName[]) => {
      if (!session) return false;
      return roles.some((role) => session.roles.includes(role));
    },
    [session],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      isLoading,
      isAuthenticated: Boolean(session),
      roles: session?.roles ?? [],
      login,
      register,
      logout,
      refresh: loadSession,
      can,
      hasRole,
    }),
    [session, isLoading, login, register, logout, loadSession, can, hasRole],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}

/** Route guard for dashboard areas. */
export function useRequireAuth(allowedRoles?: RoleName[]) {
  const { session, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (!session) {
      const next =
        typeof window !== "undefined"
          ? `?next=${encodeURIComponent(window.location.pathname)}`
          : "";
      router.replace(`/login${next}`);
      return;
    }
    if (
      allowedRoles?.length &&
      !allowedRoles.some((role) => session.roles.includes(role)) &&
      !session.roles.includes("SUPER_ADMIN")
    ) {
      router.replace(session.home_route);
    }
  }, [session, isLoading, allowedRoles, router]);

  return { session, isLoading };
}
