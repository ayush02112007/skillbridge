"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight, BookOpen, CheckCircle2, Circle, Clock, Target, TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { RadarChartCard } from "@/components/charts/charts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { Progress, ScoreRing } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState, ErrorState, SkeletonList, SkeletonStats } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { PROFICIENCY_ORDER } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type {
  GapItem, JobRole, LearningPath, Paged, RoleReadiness, SkillGap, StudentProfile,
} from "@/types/api";

function levelValue(level: string): number {
  const index = PROFICIENCY_ORDER.indexOf(level as never);
  return index < 0 ? 0 : index;
}

function GapRow({ item }: { item: GapItem }) {
  const tone =
    item.status === "STRONG" ? "success" : item.status === "WEAK" ? "warning" : "danger";
  const icon =
    item.status === "STRONG" ? (
      <CheckCircle2 className="size-4 text-success-500" aria-hidden />
    ) : (
      <Circle className={cn("size-4", item.status === "WEAK" ? "text-warning-500" : "text-danger-500")} aria-hidden />
    );

  return (
    <li className="flex gap-3 py-3.5">
      {item.status !== "STRONG" ? (
        <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-ink-100 text-2xs font-semibold text-ink-600">
          {item.priority}
        </span>
      ) : (
        <span className="flex size-6 shrink-0 items-center justify-center">{icon}</span>
      )}

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-medium text-ink-900">{item.skill_name}</p>
          <Badge tone={tone}>
            {item.status === "STRONG" ? "Meets the bar" : item.status === "WEAK" ? "Needs work" : "Missing"}
          </Badge>
          <Badge tone="outline">{item.importance.toLowerCase()}</Badge>
        </div>
        <p className="mt-1 text-xs text-ink-500">
          You: <strong className="font-medium text-ink-700">
            {item.current_level === "NONE" ? "not started" : item.current_level.toLowerCase()}
          </strong>
          {" · "}
          Role expects: <strong className="font-medium text-ink-700">
            {item.required_level.toLowerCase()}
          </strong>
        </p>
        {item.status !== "STRONG" && (
          <p className="mt-1.5 text-xs leading-relaxed text-ink-600">{item.recommendation}</p>
        )}
      </div>

      <div className="hidden w-24 shrink-0 self-center sm:block">
        <Progress value={item.coverage * 100} size="sm" />
      </div>
    </li>
  );
}

function LearningPathPanel({ jobRoleId }: { jobRoleId?: string }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["learning-path", jobRoleId],
    queryFn: () =>
      api.get<LearningPath>("/recommendations/learning-path", {
        job_role_id: jobRoleId,
      }),
    enabled: Boolean(jobRoleId),
  });

  if (isLoading) return <SkeletonList count={3} rows={2} />;
  if (error) return <ErrorState error={error} onRetry={() => void refetch()} />;
  if (!data) return null;

  if (data.steps.length === 0) {
    return (
      <EmptyState
        icon={<CheckCircle2 />}
        title="Nothing left to close"
        description={`You already meet every recorded requirement for ${data.job_role_title}.`}
      />
    );
  }

  return (
    <div>
      <Card className="mb-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="text-sm font-medium text-ink-900">{data.title}</p>
            <p className="mt-1 text-sm leading-relaxed text-ink-600">{data.summary}</p>
          </div>
          <div className="flex shrink-0 gap-5">
            <div className="text-center">
              <p className="text-xl font-semibold tabular-nums text-ink-900">
                {data.total_hours}h
              </p>
              <p className="text-2xs text-ink-500">of study</p>
            </div>
            <div className="text-center">
              <p className="text-xl font-semibold tabular-nums text-ink-900">
                ~{data.estimated_weeks}w
              </p>
              <p className="text-2xs text-ink-500">at 8h/week</p>
            </div>
          </div>
        </div>
      </Card>

      <ol className="relative space-y-3 border-l border-ink-200 pl-6">
        {data.steps.map((step) => (
          <li key={step.skill_id} className="relative">
            <span
              className="absolute -left-[31px] top-4 flex size-6 items-center justify-center rounded-full border-2 border-surface bg-primary text-2xs font-semibold text-primary-fg"
              aria-hidden
            >
              {step.order}
            </span>
            <Card className="p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-ink-900">{step.skill_name}</p>
                  <p className="mt-0.5 text-xs text-ink-500">
                    {step.current_level === "NONE" ? "Not started" : step.current_level.toLowerCase()}
                    {" → "}
                    {step.target_level.toLowerCase()}
                  </p>
                </div>
                <Badge tone="neutral" size="md">
                  <Clock className="size-3" aria-hidden />
                  {step.estimated_hours}h
                </Badge>
              </div>

              <p className="mt-2 text-xs leading-relaxed text-ink-600">{step.why}</p>

              {step.prerequisites.length > 0 && (
                <p className="mt-2 text-2xs text-ink-500">
                  Best learned after: {step.prerequisites.join(", ")}
                </p>
              )}

              {step.programs.length > 0 && (
                <div className="mt-3 space-y-1.5 border-t border-ink-100 pt-3">
                  <p className="text-2xs font-semibold uppercase tracking-wide text-ink-500">
                    Programmes covering this
                  </p>
                  {step.programs.map((program) => (
                    <Link
                      key={program.id}
                      href={`/student/learning?program=${program.id}`}
                      className="flex items-center justify-between gap-2 rounded-lg bg-surface-muted px-2.5 py-1.5 text-xs transition-colors hover:bg-ink-100"
                    >
                      <span className="min-w-0 truncate text-ink-800">{program.title}</span>
                      <span className="shrink-0 text-ink-500">
                        {program.duration_hours}h{program.is_free ? " · Free" : ""}
                      </span>
                    </Link>
                  ))}
                </div>
              )}
            </Card>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function SkillGapAnalysis() {
  const queryClient = useQueryClient();
  const [selectedRole, setSelectedRole] = useState<string>("");

  const profileQuery = useQuery({
    queryKey: ["student", "profile"],
    queryFn: () => api.get<StudentProfile>("/students/me"),
  });

  const rolesQuery = useQuery({
    queryKey: ["job-roles", "all"],
    queryFn: () => api.paged<JobRole>("/job-roles", { page_size: 60 }) as Promise<Paged<JobRole>>,
    staleTime: 10 * 60_000,
  });

  const roleId = selectedRole || profileQuery.data?.target_job_role_id || "";

  const gapQuery = useQuery({
    queryKey: ["skill-gap", roleId],
    queryFn: () => api.get<SkillGap>("/students/me/skill-gap", { job_role_id: roleId }),
    enabled: Boolean(roleId),
  });

  const readinessQuery = useQuery({
    queryKey: ["role-readiness"],
    queryFn: () => api.get<RoleReadiness[]>("/students/me/role-readiness", { limit: 6 }),
  });

  const setTarget = useMutation({
    mutationFn: (jobRoleId: string) =>
      api.patch<StudentProfile>("/students/me", { target_job_role_id: jobRoleId }),
    onSuccess: (profile) => {
      toast.success(`Target role set to ${profile.target_job_role_title}`);
      void queryClient.invalidateQueries({ queryKey: ["student"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not set target role"),
  });

  const gap = gapQuery.data;
  const radarData =
    gap?.items.slice(0, 8).map((item) => ({
      subject: item.skill_name.length > 14 ? `${item.skill_name.slice(0, 13)}…` : item.skill_name,
      you: levelValue(item.current_level),
      required: levelValue(item.required_level),
    })) ?? [];

  return (
    <>
      <PageHeader
        title="Skill gap analysis"
        description="Compare what you can evidence against what industry asks for, and get the difference as an ordered plan."
        actions={
          roleId && profileQuery.data?.target_job_role_id !== roleId ? (
            <Button
              onClick={() => setTarget.mutate(roleId)}
              isLoading={setTarget.isPending}
              leftIcon={<Target />}
            >
              Make this my target role
            </Button>
          ) : undefined
        }
      >
        <Select
          label="Target role"
          value={roleId}
          onChange={(event) => setSelectedRole(event.target.value)}
          className="max-w-sm"
        >
          <option value="">Choose a role to analyse</option>
          {rolesQuery.data?.data.map((role) => (
            <option key={role.id} value={role.id}>
              {role.title} — {role.family}
            </option>
          ))}
        </Select>
      </PageHeader>

      {!roleId && (
        <>
          <EmptyState
            icon={<Target />}
            title="Choose a role to see your gap"
            description="Select any role above, or start from the roles you are already closest to."
          />
          {readinessQuery.data && readinessQuery.data.length > 0 && (
            <Card className="mt-5">
              <CardHeader>
                <CardTitle>Roles you are closest to</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="divide-y divide-ink-100">
                  {readinessQuery.data.map((role) => (
                    <li key={role.job_role_id} className="flex items-center gap-4 py-3">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-ink-900">{role.title}</p>
                        <p className="truncate text-xs text-ink-500">
                          {role.matched_count}/{role.total_required} requirements met
                          {role.top_missing.length > 0 && ` · missing ${role.top_missing.slice(0, 2).join(", ")}`}
                        </p>
                      </div>
                      <div className="w-24 shrink-0">
                        <Progress value={role.readiness_score} size="sm" showValue />
                      </div>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setSelectedRole(role.job_role_id)}
                      >
                        Analyse
                      </Button>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {roleId && gapQuery.isLoading && <SkeletonStats />}
      {roleId && gapQuery.error && (
        <ErrorState error={gapQuery.error} onRetry={() => void gapQuery.refetch()} />
      )}

      {gap && (
        <>
          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-1">
              <CardHeader>
                <CardTitle>Readiness for {gap.job_role_title}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-center">
                  <ScoreRing value={gap.readiness_score} size={150} sublabel="ready" />
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-lg bg-success-50 p-2.5">
                    <p className="text-lg font-semibold tabular-nums text-success-700">
                      {gap.strong_skills.length}
                    </p>
                    <p className="text-2xs text-success-700">meet the bar</p>
                  </div>
                  <div className="rounded-lg bg-warning-50 p-2.5">
                    <p className="text-lg font-semibold tabular-nums text-warning-600">
                      {gap.weak_skills.length}
                    </p>
                    <p className="text-2xs text-warning-600">need work</p>
                  </div>
                  <div className="rounded-lg bg-danger-50 p-2.5">
                    <p className="text-lg font-semibold tabular-nums text-danger-600">
                      {gap.missing_skills.length}
                    </p>
                    <p className="text-2xs text-danger-600">missing</p>
                  </div>
                </div>
                <p className="text-sm leading-relaxed text-ink-600">{gap.summary}</p>
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>You vs the role</CardTitle>
                <p className="text-sm text-ink-500">
                  Each axis is a required skill; the outer shape is what the role expects.
                </p>
              </CardHeader>
              <CardContent>
                <RadarChartCard data={radarData} />
              </CardContent>
            </Card>
          </div>

          <Tabs defaultValue="priorities" className="mt-6">
            <TabsList ariaLabel="Gap views">
              <TabsTrigger value="priorities">Priorities</TabsTrigger>
              <TabsTrigger value="all">All requirements</TabsTrigger>
              <TabsTrigger value="path">Learning path</TabsTrigger>
            </TabsList>

            <TabsContent value="priorities">
              <Card>
                <CardHeader>
                  <CardTitle>Close these first</CardTitle>
                  <p className="text-sm text-ink-500">
                    Ordered by importance to the role, size of the gap and market demand.
                  </p>
                </CardHeader>
                <CardContent>
                  {gap.priority_skills.length === 0 ? (
                    <EmptyState
                      className="border-0 bg-transparent"
                      icon={<CheckCircle2 />}
                      title="Nothing outstanding"
                      description="You meet every recorded requirement for this role."
                    />
                  ) : (
                    <ul className="divide-y divide-ink-100">
                      {gap.priority_skills.map((item) => (
                        <GapRow key={item.skill_id} item={item} />
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="all">
              <Card>
                <CardHeader>
                  <CardTitle>
                    Every requirement ({gap.matched_count}/{gap.total_required} core met)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="divide-y divide-ink-100">
                    {gap.items.map((item) => (
                      <GapRow key={item.skill_id} item={item} />
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="path">
              <LearningPathPanel jobRoleId={roleId} />
            </TabsContent>
          </Tabs>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/student/assessment">
              <Button variant="secondary" leftIcon={<TrendingUp />}>
                Evidence a skill with an assessment
              </Button>
            </Link>
            <Link href="/student/learning">
              <Button variant="secondary" leftIcon={<BookOpen />}>
                Browse learning programmes
              </Button>
            </Link>
            <Link href="/student/internships">
              <Button rightIcon={<ArrowRight />}>See matched internships</Button>
            </Link>
          </div>
        </>
      )}
    </>
  );
}
