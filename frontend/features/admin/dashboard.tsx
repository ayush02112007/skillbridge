"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Activity, Briefcase, Building2, GraduationCap, Shield, Sparkles, Users,
} from "lucide-react";
import Link from "next/link";

import { DonutChartCard, LineChartCard } from "@/components/charts/charts";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Stat } from "@/components/ui/stat";
import { ErrorState, SkeletonStats } from "@/components/ui/states";
import { api } from "@/lib/api";
import { ROLE_LABELS } from "@/lib/constants";
import type { RoleName } from "@/types/api";

interface PlatformAnalytics {
  summary: Record<string, number>;
  users_by_role: Record<string, number>;
  signup_trend: { months: string[]; signups: number[] };
}

interface SystemHealth {
  environment: string;
  database: string;
  cache: string;
  storage: string;
  ai_provider: string;
  email_provider: string;
  debug: boolean;
  match_weights: Record<string, number>;
  config_problems: string[];
}

export function AdminDashboard() {
  const analytics = useQuery({
    queryKey: ["admin", "analytics"],
    queryFn: () => api.get<PlatformAnalytics>("/admin/analytics"),
  });

  const health = useQuery({
    queryKey: ["admin", "health"],
    queryFn: () => api.get<SystemHealth>("/admin/system/health"),
  });

  if (analytics.isLoading) {
    return (
      <>
        <PageHeader title="Platform dashboard" />
        <SkeletonStats />
      </>
    );
  }
  if (analytics.error || !analytics.data) {
    return (
      <>
        <PageHeader title="Platform dashboard" />
        <ErrorState error={analytics.error} onRetry={() => void analytics.refetch()} />
      </>
    );
  }

  const { summary, users_by_role, signup_trend } = analytics.data;
  const trendData = signup_trend.months.map((month, index) => ({
    month: month.slice(5),
    signups: signup_trend.signups[index],
  }));
  const roleData = Object.entries(users_by_role).map(([role, count]) => ({
    name: ROLE_LABELS[role as RoleName] ?? role,
    value: count,
  }));

  return (
    <>
      <PageHeader
        title="Platform dashboard"
        description="Health, growth and the state of the catalogue that everything else depends on."
        actions={
          <>
            <Link href="/admin/skills">
              <Button variant="secondary" leftIcon={<Sparkles />}>Manage taxonomy</Button>
            </Link>
            <Link href="/admin/audit">
              <Button leftIcon={<Shield />}>Audit log</Button>
            </Link>
          </>
        }
      />

      {health.data && health.data.config_problems.length > 0 && (
        <Card className="mb-5 border-danger-500/30 bg-danger-50 p-4">
          <p className="text-sm font-semibold text-danger-700">
            Configuration problems detected
          </p>
          <ul className="mt-1.5 space-y-0.5">
            {health.data.config_problems.map((problem) => (
              <li key={problem} className="text-sm text-danger-700">• {problem}</li>
            ))}
          </ul>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Users" value={summary.total_users} sublabel={`${summary.students} students`} icon={<Users />} tone="brand" />
        <Stat label="Organisations" value={summary.companies + summary.institutions} sublabel={`${summary.companies} companies · ${summary.institutions} institutions`} icon={<Building2 />} tone="accent" />
        <Stat label="Opportunities" value={summary.published_opportunities} sublabel={`${summary.opportunities} total`} icon={<Briefcase />} tone="success" />
        <Stat label="Applications" value={summary.applications} sublabel={`${summary.placements} placements made`} icon={<GraduationCap />} tone="ink" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Sign-ups over twelve months</CardTitle>
          </CardHeader>
          <CardContent>
            <LineChartCard
              data={trendData}
              xKey="month"
              area
              lines={[{ key: "signups", name: "New accounts" }]}
              emptyLabel="No sign-up data yet"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Accounts by role</CardTitle>
          </CardHeader>
          <CardContent>
            <DonutChartCard data={roleData} emptyLabel="No accounts yet" />
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Catalogue</CardTitle>
            <p className="text-sm text-ink-500">
              The reference data every recommendation depends on
            </p>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-4">
              {[
                ["Skills tracked", summary.skills_tracked],
                ["Assessments completed", summary.assessments_completed],
                ["Events", summary.events],
                ["Placements", summary.placements],
              ].map(([label, value]) => (
                <div key={label as string} className="rounded-xl bg-surface-muted p-4">
                  <dd className="text-xl font-semibold tabular-nums text-ink-900">
                    {value as number}
                  </dd>
                  <dt className="text-xs text-ink-500">{label as string}</dt>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center gap-2">
            <Activity className="size-4 text-ink-400" aria-hidden />
            <CardTitle>System</CardTitle>
          </CardHeader>
          <CardContent>
            {health.data ? (
              <dl className="space-y-2 text-sm">
                {[
                  ["Environment", health.data.environment],
                  ["Database", health.data.database],
                  ["Cache", health.data.cache],
                  ["Storage", health.data.storage],
                  ["AI provider", health.data.ai_provider],
                  ["Email provider", health.data.email_provider],
                ].map(([label, value]) => (
                  <div key={label} className="flex items-center justify-between gap-2">
                    <dt className="text-ink-500">{label}</dt>
                    <dd>
                      <Badge tone={value === "deterministic" ? "neutral" : "brand"}>
                        {value}
                      </Badge>
                    </dd>
                  </div>
                ))}
                <div className="flex items-center justify-between gap-2 border-t border-ink-100 pt-2">
                  <dt className="text-ink-500">Matching weights</dt>
                  <dd className="text-xs tabular-nums text-ink-700">
                    skills {Math.round(health.data.match_weights.skills * 100)}% ·
                    education {Math.round(health.data.match_weights.education * 100)}%
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-ink-500">Loading system status…</p>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
