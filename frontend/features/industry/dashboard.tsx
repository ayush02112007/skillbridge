"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Briefcase, Clock, Eye, Plus, TrendingUp, UserCheck, Users,
} from "lucide-react";
import Link from "next/link";

import { FunnelChart, BarChartCard } from "@/components/charts/charts";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Stat } from "@/components/ui/stat";
import { EmptyState, ErrorState, SkeletonStats } from "@/components/ui/states";
import { api } from "@/lib/api";
import { APPLICATION_STATUS_LABELS, APPLICATION_STATUS_TONE } from "@/lib/constants";
import { formatDate, relativeTime } from "@/lib/utils";
import type { ApplicationStatus } from "@/types/api";

interface IndustryDashboardData {
  company: { id: string; name: string; slug: string; industry_sector: string };
  summary: {
    total_postings: number;
    active_postings: number;
    total_applicants: number;
    qualified_applicants: number;
    qualified_rate: number;
    average_match_score: number;
    hires: number;
    average_time_to_hire_days: number | null;
  };
  hiring_funnel: { stage: string; count: number }[];
  recent_applicants: {
    application_id: string;
    student_name: string;
    opportunity_title: string;
    match_score: number;
    status: ApplicationStatus;
    submitted_at: string;
  }[];
  active_postings: {
    id: string;
    title: string;
    type: string;
    applications: number;
    views: number;
    deadline: string | null;
  }[];
  skill_shortfall: { skill: string; applicants_missing: number }[];
}

export function IndustryDashboard() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["industry", "dashboard"],
    queryFn: () => api.get<IndustryDashboardData>("/companies/me/dashboard"),
  });

  if (isLoading) {
    return (
      <>
        <PageHeader title="Overview" />
        <SkeletonStats />
      </>
    );
  }
  if (error || !data) {
    return (
      <>
        <PageHeader title="Overview" />
        <ErrorState error={error} onRetry={() => void refetch()} />
      </>
    );
  }

  const { summary } = data;

  return (
    <>
      <PageHeader
        title={data.company.name}
        description="Your hiring pipeline, applicant quality and where candidates fall short."
        actions={
          <>
            <Link href="/industry/internships">
              <Button variant="secondary" leftIcon={<Plus />}>Post internship</Button>
            </Link>
            <Link href="/industry/jobs">
              <Button leftIcon={<Plus />}>Post a job</Button>
            </Link>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Active postings"
          value={summary.active_postings}
          sublabel={`${summary.total_postings} total`}
          icon={<Briefcase />}
          tone="brand"
        />
        <Stat
          label="Applicants"
          value={summary.total_applicants}
          sublabel={`${summary.qualified_applicants} above 70% match`}
          icon={<Users />}
          tone="accent"
        />
        <Stat
          label="Average match"
          value={`${summary.average_match_score}%`}
          sublabel="Across all applicants"
          icon={<TrendingUp />}
          tone="success"
        />
        <Stat
          label="Time to hire"
          value={
            summary.average_time_to_hire_days !== null
              ? `${summary.average_time_to_hire_days}d`
              : "—"
          }
          sublabel={`${summary.hires} hire(s) made`}
          icon={<Clock />}
          tone="ink"
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Hiring funnel</CardTitle>
            <p className="text-sm text-ink-500">Conversion between each stage</p>
          </CardHeader>
          <CardContent>
            <FunnelChart stages={data.hiring_funnel} />
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Where applicants fall short</CardTitle>
            <p className="text-sm text-ink-500">
              The skills most often missing from your applicant pool — useful for
              tuning requirements, or for deciding what to train.
            </p>
          </CardHeader>
          <CardContent>
            <BarChartCard
              data={data.skill_shortfall.slice(0, 8)}
              xKey="skill"
              bars={[{ key: "applicants_missing", name: "Applicants missing it" }]}
              layout="vertical"
              height={280}
              emptyLabel="No applicant data yet"
            />
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-3">
            <CardTitle>Recent applicants</CardTitle>
            <Link href="/industry/applicants">
              <Button variant="secondary" size="sm">Review all</Button>
            </Link>
          </CardHeader>
          <CardContent>
            {data.recent_applicants.length === 0 ? (
              <EmptyState
                className="border-0 bg-transparent py-6"
                icon={<UserCheck />}
                title="No applicants yet"
                description="Publish a posting with clear skill requirements and matched students will find it."
              />
            ) : (
              <ul className="divide-y divide-ink-100">
                {data.recent_applicants.map((applicant) => (
                  <li key={applicant.application_id}>
                    <Link
                      href={`/industry/applicants?application=${applicant.application_id}`}
                      className="flex items-center gap-3 py-3 transition-colors hover:bg-surface-muted/60"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-ink-900">
                          {applicant.student_name}
                        </p>
                        <p className="truncate text-xs text-ink-500">
                          {applicant.opportunity_title} · {relativeTime(applicant.submitted_at)}
                        </p>
                      </div>
                      <span className="shrink-0 text-xs tabular-nums text-ink-600">
                        {Math.round(applicant.match_score)}%
                      </span>
                      <Badge tone={APPLICATION_STATUS_TONE[applicant.status]}>
                        {APPLICATION_STATUS_LABELS[applicant.status]}
                      </Badge>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Active postings</CardTitle>
          </CardHeader>
          <CardContent>
            {data.active_postings.length === 0 ? (
              <EmptyState
                className="border-0 bg-transparent py-6"
                icon={<Briefcase />}
                title="No active postings"
                description="Publish a role to start receiving matched applicants."
                action={
                  <Link href="/industry/jobs">
                    <Button size="sm">Post a job</Button>
                  </Link>
                }
              />
            ) : (
              <ul className="divide-y divide-ink-100">
                {data.active_postings.map((posting) => (
                  <li key={posting.id} className="flex items-center gap-3 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-ink-900">
                        {posting.title}
                      </p>
                      <p className="text-xs text-ink-500">
                        {posting.deadline
                          ? `Closes ${formatDate(posting.deadline)}`
                          : "No deadline"}
                      </p>
                    </div>
                    <span className="flex shrink-0 items-center gap-1 text-xs text-ink-500">
                      <Eye className="size-3.5" aria-hidden />
                      {posting.views}
                    </span>
                    <Badge tone="brand">{posting.applications} applied</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
