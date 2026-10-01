"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, LogOut, Monitor, Save, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { Input } from "@/components/ui/input";
import { ErrorState, SkeletonCard } from "@/components/ui/states";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ROLE_LABELS } from "@/lib/constants";
import { formatDateTime, relativeTime } from "@/lib/utils";

interface SessionRow {
  id: string;
  user_agent?: string | null;
  ip_address?: string | null;
  created_at: string;
  expires_at: string;
  is_current: boolean;
}

export function SettingsPage() {
  const { session, logout, refresh } = useAuth();
  const queryClient = useQueryClient();
  const [profile, setProfile] = useState({
    full_name: session?.user.full_name ?? "",
    phone: session?.user.phone ?? "",
    timezone_name: session?.user.timezone_name ?? "UTC",
  });
  const [passwords, setPasswords] = useState({ current_password: "", new_password: "" });

  const sessions = useQuery({
    queryKey: ["auth", "sessions"],
    queryFn: () => api.get<SessionRow[]>("/auth/sessions"),
  });

  const saveProfile = useMutation({
    mutationFn: () => api.patch("/auth/me", profile),
    onSuccess: async () => {
      toast.success("Account updated");
      await refresh();
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not save"),
  });

  const changePassword = useMutation({
    mutationFn: () => api.post("/auth/change-password", passwords),
    onSuccess: () => {
      toast.success("Password changed — sign in again with your new password");
      setPasswords({ current_password: "", new_password: "" });
      void logout();
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not change password"),
  });

  const revokeSession = useMutation({
    mutationFn: (id: string) => api.delete(`/auth/sessions/${id}`),
    onSuccess: () => {
      toast.success("Session revoked");
      void queryClient.invalidateQueries({ queryKey: ["auth", "sessions"] });
    },
  });

  if (!session) return <SkeletonCard rows={4} />;

  return (
    <>
      <PageHeader
        title="Settings"
        description="Your account, security and active sessions."
      />

      <Tabs defaultValue="account">
        <TabsList ariaLabel="Settings sections">
          <TabsTrigger value="account">Account</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
          <TabsTrigger value="sessions">Devices</TabsTrigger>
        </TabsList>

        <TabsContent value="account">
          {/* Appearance */}
          <Card>
            <CardHeader>
              <CardTitle>Appearance</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-ink-600">
                Choose a colour theme. &ldquo;System&rdquo; follows your device
                and keeps following it when your device switches.
              </p>
              <ThemeToggle menu />
              <p className="text-xs text-ink-500">
                Your choice is stored on this device and applies the next time
                you open SkillBridge.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Account details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm text-ink-500">Signed in as</span>
                <span className="text-sm font-medium text-ink-900">
                  {session.user.email}
                </span>
                {session.roles.map((role) => (
                  <Badge key={role} tone="brand">{ROLE_LABELS[role]}</Badge>
                ))}
                {session.user.is_email_verified && (
                  <Badge tone="success">
                    <ShieldCheck className="size-3" aria-hidden />
                    Verified
                  </Badge>
                )}
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Full name"
                  value={profile.full_name}
                  onChange={(event) =>
                    setProfile((c) => ({ ...c, full_name: event.target.value }))
                  }
                />
                <Input
                  label="Phone"
                  value={profile.phone ?? ""}
                  onChange={(event) =>
                    setProfile((c) => ({ ...c, phone: event.target.value }))
                  }
                />
                <Input
                  label="Time zone"
                  value={profile.timezone_name}
                  hint="Used when showing interview and session times."
                  onChange={(event) =>
                    setProfile((c) => ({ ...c, timezone_name: event.target.value }))
                  }
                />
              </div>

              <Button
                isLoading={saveProfile.isPending}
                onClick={() => saveProfile.mutate()}
                leftIcon={<Save />}
              >
                Save changes
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>Change password</CardTitle>
              <p className="text-sm text-ink-500">
                Changing your password signs out every device, including this one.
              </p>
            </CardHeader>
            <CardContent className="max-w-md space-y-4">
              <Input
                label="Current password"
                type="password"
                autoComplete="current-password"
                value={passwords.current_password}
                onChange={(event) =>
                  setPasswords((c) => ({ ...c, current_password: event.target.value }))
                }
              />
              <Input
                label="New password"
                type="password"
                autoComplete="new-password"
                hint="At least 10 characters with upper and lowercase, a digit and a symbol."
                value={passwords.new_password}
                onChange={(event) =>
                  setPasswords((c) => ({ ...c, new_password: event.target.value }))
                }
              />
              <Button
                isLoading={changePassword.isPending}
                disabled={!passwords.current_password || passwords.new_password.length < 10}
                onClick={() => changePassword.mutate()}
                leftIcon={<KeyRound />}
              >
                Change password
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sessions">
          <Card>
            <CardHeader>
              <CardTitle>Active sessions</CardTitle>
              <p className="text-sm text-ink-500">
                Every device holding a valid session. Revoke anything you do not
                recognise.
              </p>
            </CardHeader>
            <CardContent>
              {sessions.isLoading && <SkeletonCard rows={3} />}
              {sessions.error && (
                <ErrorState error={sessions.error} onRetry={() => void sessions.refetch()} />
              )}
              <ul className="divide-y divide-ink-100">
                {sessions.data?.map((row) => (
                  <li key={row.id} className="flex items-center gap-3 py-3">
                    <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-ink-100 text-ink-500">
                      <Monitor className="size-4" aria-hidden />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-ink-800">
                        {row.user_agent?.slice(0, 70) ?? "Unknown device"}
                        {row.is_current && (
                          <Badge tone="success" className="ml-2">This device</Badge>
                        )}
                      </p>
                      <p className="text-xs text-ink-500">
                        {row.ip_address ?? "—"} · started {relativeTime(row.created_at)} ·
                        expires {formatDateTime(row.expires_at)}
                      </p>
                    </div>
                    {!row.is_current && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => revokeSession.mutate(row.id)}
                      >
                        Revoke
                      </Button>
                    )}
                  </li>
                ))}
              </ul>

              <div className="mt-4 border-t border-ink-100 pt-4">
                <Button variant="danger" onClick={() => void logout()} leftIcon={<LogOut />}>
                  Sign out
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </>
  );
}
