"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Award, ArrowRight, BookOpen, Briefcase, Calendar, ClipboardCheck,
  ExternalLink, Target, TrendingUp, Users,
} from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress, ScoreRing } from "@/components/ui/progress";
import { SkillBadge } from "@/components/ui/skill-badge";
import { Stat } from "@/components/ui/stat";
import {
  EmptyState, ErrorState, SkeletonList, SkeletonStats,
} from "@/components/ui/states";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { APPLICATION_STATUS_LABELS, APPLICATION_STATUS_TONE } from "@/lib/constants";
import { cn, daysUntil, formatDate, relativeTime } from "@/lib/utils";
import type { OpportunityRecommendation, StudentDashboard as DashboardData } from "@/types/api";

function GapPanel({ data }: { data: DashboardData }) {
  const gap = data.skill_gap;

  if (!gap) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Choose a target role</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            className="border-0 bg-transparent py-6"
            icon={<Target />}
            title="No target role selected"
            description="Pick the role you're aiming for and we'll show exactly which skills you're missing, in priority order."
            action={
              <Link href="/student/careers">
                <Button size="sm" rightIcon={<ArrowRight />}>Explore career roles</Button>
              </Link>
            }
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3">
        <div>
          <CardTitle>Your gap for {gap.job_role_title}</CardTitle>
          <p className="mt-1 text-sm text-ink-500">
            {gap.matched_count} of {gap.total_required} core requirements met
          </p>
        </div>
        <Link href="/student/skill-gap">
          <Button variant="secondary" size="sm">Full analysis</Button>
        </Link>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm leading-relaxed text-ink-600">{gap.summary}</p>

        {gap.priority_skills.length > 0 ? (
          <ol className="space-y-2.5">
            {gap.priority_skills.map((item) => (
              <li key={item.skill_id} className="flex items-center gap-3">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-ink-100 text-2xs font-semibold text-ink-600">
                  {item.priority}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-ink-900">
                    {item.skill_name}
                  </span>
                  <span className="block text-xs text-ink-500">
                    {item.current_level === "NONE" ? "Not started" : item.current_level.toLowerCase()}
                    {" → "}
                    {item.required_level.toLowerCase()}
                  </span>
                </span>
                <Badge tone={item.status === "MISSING" ? "danger" : "warning"}>
                  {item.status === "MISSING" ? "Missing" : "Needs work"}
                </Badge>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-success-700">
            You meet every recorded requirement for this role.
          </p>
        )}

        <Link href="/student/learning">
          <Button variant="subtle" size="sm" block rightIcon={<ArrowRight />}>
            See the learning path that closes this
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}

function RecommendationsPanel() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["recommendations", "internships", "dashboard"],
    queryFn: () =>
      api.get<OpportunityRecommendation[]>("/recommendations/internships", { limit: 3 }),
  });

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3">
        <div>
          <CardTitle>Recommended for you</CardTitle>
          <p className="mt-1 text-sm text-ink-500">
            Ranked by evidenced skill fit — every one explains itself
          </p>
        </div>
        <Link href="/student/internships">
          <Button variant="secondary" size="sm">Browse all</Button>
        </Link>
      </CardHeader>
      <CardContent>
        {isLoading && <SkeletonList count={2} rows={2} />}
        {error && <ErrorState error={error} onRetry={() => void refetch()} />}
        {data && data.length === 0 && (
          <EmptyState
            className="border-0 bg-transparent py-6"
            icon={<Briefcase />}
            title="No matches yet"
            description="Add a few more skills or take an assessment, and recommendations will appear here."
            action={
              <Link href="/student/assessment">
                <Button size="sm">Take an assessment</Button>
              </Link>
            }
          />
        )}
        {data && data.length > 0 && (
          <ul className="space-y-3">
            {data.map((item) => (
              <li key={item.target_id}>
                <Link
                  href={`/opportunities/${item.target_id}`}
                  className="block rounded-xl border border-ink-200 p-4 transition-all hover:-translate-y-0.5 hover:border-ink-300 hover:shadow-card"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-ink-900">
                        {item.target_title}
                      </p>
                      <p className="truncate text-xs text-ink-500">
                        {item.company_name}
                        {item.location_city ? ` · ${item.location_city}` : ""}
                      </p>
                    </div>
                    <Badge
                      tone={item.match_score >= 70 ? "success" : item.match_score >= 50 ? "brand" : "warning"}
                      size="md"
                    >
                      {Math.round(item.match_score)}% match
                    </Badge>
                  </div>
                  <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-ink-600">
                    {item.reason_summary}
                  </p>
                  <div className="mt-2.5 flex flex-wrap gap-1">
                    {item.matching_skills.slice(0, 3).map((skill) => (
                      <Badge key={skill} tone="success">{skill}</Badge>
                    ))}
                    {item.missing_skills.slice(0, 2).map((skill) => (
                      <Badge key={skill} tone="warning">{skill} — gap</Badge>
                    ))}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export function StudentDashboard() {
  const { session } = useAuth();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["student", "dashboard"],
    queryFn: () => api.get<DashboardData>("/students/me/dashboard"),
  });

  const firstName = session?.user.full_name.split(" ")[0] ?? "there";

  if (isLoading) {
    return (
      <>
        <PageHeader title={`Welcome back, ${firstName}`} />
        <SkeletonStats />
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <SkeletonList count={2} />
          <SkeletonList count={2} />
        </div>
      </>
    );
  }

  if (error || !data) {
    return (
      <>
        <PageHeader title={`Welcome back, ${firstName}`} />
        <ErrorState error={error} onRetry={() => void refetch()} />
      </>
    );
  }

  const completion = data.profile_completion;
  const topSuggestion = completion.suggestions[0];

  return (
    <>
      <PageHeader
        title={`Welcome back, ${firstName}`}
        description="Your readiness, your gap, and the opportunities you're closest to."
        actions={
          <>
            <Link href="/student/assessment">
              <Button variant="secondary" leftIcon={<ClipboardCheck />}>
                Take an assessment
              </Button>
            </Link>
            {data.portfolio.slug && (
              <Link href={`/portfolio/${data.portfolio.slug}`} target="_blank">
                <Button leftIcon={<ExternalLink />}>View portfolio</Button>
              </Link>
            )}
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Role readiness"
          value={`${Math.round(data.skill_readiness_score)}%`}
          sublabel={data.target_role?.title ?? "Choose a target role"}
          icon={<Target />}
          tone="brand"
        />
        <Stat
          label="Applications"
          value={data.applications.total}
          sublabel={`${data.applications.interviews_scheduled} interview(s) scheduled`}
          icon={<Briefcase />}
          tone="accent"
        />
        <Stat
          label="Assessments"
          value={data.assessments.completed}
          sublabel="Completed and scored"
          icon={<ClipboardCheck />}
          tone="success"
        />
        <Stat
          label="Learning"
          value={data.learning.active_enrollments}
          sublabel={`${data.learning.certifications} certification(s) earned`}
          icon={<BookOpen />}
          tone="ink"
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        {/* Readiness + profile completion */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Where you stand</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex justify-center">
              <ScoreRing
                value={data.skill_readiness_score}
                size={140}
                label="Role readiness"
                sublabel={data.target_role?.title ?? "No target role"}
              />
            </div>

            <div className="space-y-2">
              <Progress
                value={completion.percentage}
                label="Profile completion"
                showValue
                tone="brand"
              />
              {topSuggestion && (
                <Link
                  href={topSuggestion.url}
                  className="flex items-center justify-between gap-2 rounded-lg bg-surface-muted px-3 py-2 text-xs transition-colors hover:bg-ink-100"
                >
                  <span className="min-w-0 truncate text-ink-700">
                    {topSuggestion.action}
                  </span>
                  <span className="shrink-0 font-semibold text-brand-700">
                    +{topSuggestion.impact}%
                  </span>
                </Link>
              )}
            </div>

            {data.top_skills.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
                  Strongest skills
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {data.top_skills.slice(0, 5).map((skill) => (
                    <SkillBadge
                      key={skill.skill_id}
                      name={skill.name}
                      level={skill.level}
                      source={skill.source}
                      confidence={skill.confidence}
                    />
                  ))}
                </div>
              </div>
            )}

            {data.badges.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
                  Badges earned
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {data.badges.map((badge) => (
                    <Badge key={badge.code} tone="accent" size="md">
                      <Award className="size-3" aria-hidden />
                      {badge.name}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6 lg:col-span-2">
          <GapPanel data={data} />
          <RecommendationsPanel />
        </div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        {/* Applications */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-start justify-between gap-3">
            <CardTitle>Recent applications</CardTitle>
            <Link href="/student/applications">
              <Button variant="secondary" size="sm">Track all</Button>
            </Link>
          </CardHeader>
          <CardContent>
            {data.applications.recent.length === 0 ? (
              <EmptyState
                className="border-0 bg-transparent py-6"
                icon={<Briefcase />}
                title="No applications yet"
                description="When you apply, you'll be able to follow each application through every stage here."
                action={
                  <Link href="/student/internships">
                    <Button size="sm">Find internships</Button>
                  </Link>
                }
              />
            ) : (
              <ul className="divide-y divide-ink-100">
                {data.applications.recent.map((application) => (
                  <li key={application.id}>
                    <Link
                      href={`/student/applications?highlight=${application.id}`}
                      className="flex items-center gap-3 py-3 transition-colors hover:bg-surface-muted/60"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-ink-900">
                          {application.opportunity_title}
                        </p>
                        <p className="truncate text-xs text-ink-500">
                          {application.company_name} · applied {relativeTime(application.submitted_at)}
                        </p>
                      </div>
                      <span className="hidden shrink-0 text-xs tabular-nums text-ink-500 sm:block">
                        {Math.round(application.match_score)}% match
                      </span>
                      <Badge tone={APPLICATION_STATUS_TONE[application.status]} size="md">
                        {APPLICATION_STATUS_LABELS[application.status]}
                      </Badge>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Deadlines */}
        <Card>
          <CardHeader>
            <CardTitle>Closing soon</CardTitle>
          </CardHeader>
          <CardContent>
            {data.upcoming_deadlines.length === 0 ? (
              <EmptyState
                className="border-0 bg-transparent py-6"
                icon={<Calendar />}
                title="Nothing closing soon"
                description="Save opportunities and we'll remind you before the deadline."
              />
            ) : (
              <ul className="space-y-3">
                {data.upcoming_deadlines.map((item) => {
                  const days = daysUntil(item.deadline);
                  return (
                    <li key={item.id}>
                      <Link
                        href={`/opportunities/${item.id}`}
                        className="block rounded-lg border border-ink-200 p-3 transition-colors hover:border-ink-300 hover:bg-surface-muted"
                      >
                        <p className="truncate text-sm font-medium text-ink-900">
                          {item.title}
                        </p>
                        <p className="truncate text-xs text-ink-500">{item.company_name}</p>
                        <p
                          className={cn(
                            "mt-1.5 text-xs font-medium",
                            days !== null && days <= 3 ? "text-danger-600" : "text-ink-600",
                          )}
                        >
                          {days !== null && days <= 0
                            ? "Closes today"
                            : `${days} day${days === 1 ? "" : "s"} left · ${formatDate(item.deadline)}`}
                        </p>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
