"use client";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { SkeletonStats } from "@/components/ui/states";
import { useRequireAuth } from "@/lib/auth";

export default function Layout({ children }: { children: React.ReactNode }) {
  const { isLoading, session } = useRequireAuth(["INDUSTRY_RECRUITER", "INDUSTRY_ADMIN"]);

  if (isLoading || !session) {
    return (
      <div className="min-h-dvh bg-surface-muted p-6">
        <SkeletonStats />
      </div>
    );
  }
  return <DashboardShell>{children}</DashboardShell>;
}
