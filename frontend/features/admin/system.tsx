"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, CheckCircle2, ShieldCheck, XCircle } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { TBody, TD, TH, THead, TR, Table, TableWrapper } from "@/components/ui/table";
import { ErrorState, SkeletonCard } from "@/components/ui/states";
import { api } from "@/lib/api";
import { MATCH_FACTOR_LABELS } from "@/lib/constants";

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

interface PermissionCatalogue {
  permissions: Record<string, string>;
  roles: Record<string, string[]>;
}

export function AdminSystem() {
  const health = useQuery({
    queryKey: ["admin", "health"],
    queryFn: () => api.get<SystemHealth>("/admin/system/health"),
  });

  const permissions = useQuery({
    queryKey: ["admin", "permissions"],
    queryFn: () => api.get<PermissionCatalogue>("/admin/system/permissions"),
  });

  return (
    <>
      <PageHeader
        title="System health"
        description="Dependency status, effective configuration and the RBAC matrix the API enforces. Secrets are never shown — only which provider is selected."
      />

      {health.isLoading && <SkeletonCard rows={5} />}
      {health.error && <ErrorState error={health.error} onRetry={() => void health.refetch()} />}

      {health.data && (
        <>
          {health.data.config_problems.length > 0 ? (
            <Card className="mb-6 border-danger-500/30 bg-danger-50 p-5">
              <p className="flex items-center gap-2 text-sm font-semibold text-danger-700">
                <XCircle className="size-4" aria-hidden />
                Configuration problems
              </p>
              <ul className="mt-2 space-y-1">
                {health.data.config_problems.map((problem) => (
                  <li key={problem} className="text-sm text-danger-700">• {problem}</li>
                ))}
              </ul>
            </Card>
          ) : (
            <Card className="mb-6 border-success-500/25 bg-success-50 p-5">
              <p className="flex items-center gap-2 text-sm font-semibold text-success-700">
                <CheckCircle2 className="size-4" aria-hidden />
                Configuration is valid for this environment
              </p>
            </Card>
          )}

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader className="flex-row items-center gap-2">
                <Activity className="size-4 text-ink-400" aria-hidden />
                <CardTitle>Runtime</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="space-y-2.5 text-sm">
                  {[
                    ["Environment", health.data.environment],
                    ["Debug mode", health.data.debug ? "on" : "off"],
                    ["Database", health.data.database],
                    ["Cache", health.data.cache],
                    ["Object storage", health.data.storage],
                    ["AI provider", health.data.ai_provider],
                    ["Email provider", health.data.email_provider],
                  ].map(([label, value]) => (
                    <div key={label} className="flex items-center justify-between gap-3">
                      <dt className="text-ink-500">{label}</dt>
                      <dd>
                        <Badge
                          tone={
                            label === "Debug mode" && value === "on"
                              ? "warning"
                              : value === "deterministic"
                                ? "neutral"
                                : "brand"
                          }
                        >
                          {value}
                        </Badge>
                      </dd>
                    </div>
                  ))}
                </dl>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Matching weights</CardTitle>
                <p className="text-sm text-ink-500">
                  Configuration, not a learned model. These are the exact weights
                  applied to every match score.
                </p>
              </CardHeader>
              <CardContent>
                <div className="space-y-2.5">
                  {Object.entries(health.data.match_weights).map(([factor, weight]) => (
                    <div key={factor} className="flex items-center gap-3">
                      <span className="w-36 shrink-0 text-xs text-ink-600">
                        {MATCH_FACTOR_LABELS[factor] ?? factor}
                      </span>
                      <Progress value={weight * 200} size="sm" className="flex-1" />
                      <span className="w-10 shrink-0 text-right text-xs font-semibold tabular-nums text-ink-800">
                        {Math.round(weight * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      {permissions.data && (
        <Card className="mt-6">
          <CardHeader className="flex-row items-center gap-2">
            <ShieldCheck className="size-4 text-ink-400" aria-hidden />
            <div>
              <CardTitle>Permission matrix</CardTitle>
              <p className="text-sm text-ink-500">
                {Object.keys(permissions.data.permissions).length} permissions across{" "}
                {Object.keys(permissions.data.roles).length} roles, exactly as the
                API enforces them.
              </p>
            </div>
          </CardHeader>
          <CardContent>
            <TableWrapper caption="Permission matrix">
              <Table>
                <THead>
                  <TR>
                    <TH>Role</TH>
                    <TH>Permissions</TH>
                  </TR>
                </THead>
                <TBody>
                  {Object.entries(permissions.data.roles).map(([role, codes]) => (
                    <TR key={role}>
                      <TD className="whitespace-nowrap align-top font-medium text-ink-900">
                        {role.replace(/_/g, " ").toLowerCase()}
                        <span className="block text-2xs font-normal text-ink-400">
                          {codes.length} permissions
                        </span>
                      </TD>
                      <TD>
                        <div className="flex flex-wrap gap-1">
                          {codes.map((code) => (
                            <Badge key={code} tone="neutral" className="font-mono">
                              {code}
                            </Badge>
                          ))}
                        </div>
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </TableWrapper>
          </CardContent>
        </Card>
      )}
    </>
  );
}
