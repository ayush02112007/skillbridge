"use client";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { SkeletonStats } from "@/components/ui/states";
import { useRequireAuth } from "@/lib/auth";

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const { isLoading, session } = useRequireAuth(["STUDENT"]);

  if (isLoading || !session) {
    return (
      <div className="min-h-dvh bg-surface-muted p-6">
        <SkeletonStats />
      </div>
    );
  }
  return <DashboardShell>{children}</DashboardShell>;
}
