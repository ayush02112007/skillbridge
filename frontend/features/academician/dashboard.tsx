"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Award, Briefcase, Calendar, FlaskConical, Users,
} from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Stat } from "@/components/ui/stat";
import { EmptyState, ErrorState, SkeletonStats } from "@/components/ui/states";
import { api } from "@/lib/api";
import { formatDate, formatDateTime } from "@/lib/utils";

interface AcademicianDashboardData {
  profile_completion: number;
  open_faculty_opportunities: number;
  my_applications: Record<string, number>;
  mentorship: Record<string, number>;
  research: Record<string, number>;
  events_hosted: number;
  upcoming_sessions: {
    id: string;
    scheduled_at: string;
    duration_minutes: number;
    agenda: string;
    meeting_link?: string | null;
  }[];
  recommended_opportunities: {
    id: string;
    title: string;
    kind: string;
    company_name: string;
    deadline?: string | null;
    overlap_count: number;
    reasons: string[];
  }[];
}

export function AcademicianDashboard() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["academician", "dashboard"],
    queryFn: () => api.get<AcademicianDashboardData>("/academicians/me/dashboard"),
  });

  if (isLoading) {
    return (
      <>
        <PageHeader title="Dashboard" />
        <SkeletonStats />
      </>
    );
  }
  if (error || !data) {
    return (
      <>
        <PageHeader title="Dashboard" />
        <ErrorState error={error} onRetry={() => void refetch()} />
      </>
    );
  }

  const totalApplications = Object.values(data.my_applications).reduce((a, b) => a + b, 0);

  return (
    <>
      <PageHeader
        title="Academician dashboard"
        description="Industry programmes open to you, your collaborations, and the students you are mentoring."
        actions={
          <Link href="/academician/opportunities">
            <Button leftIcon={<Briefcase />}>Browse faculty programmes</Button>
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Open programmes"
          value={data.open_faculty_opportunities}
          sublabel="FDPs, internships, consultancy"
          icon={<Briefcase />}
          tone="brand"
        />
        <Stat
          label="My applications"
          value={totalApplications}
          sublabel="Across all programmes"
          icon={<Award />}
          tone="accent"
        />
        <Stat
          label="Mentorship"
          value={data.mentorship.active ?? 0}
          sublabel={`${data.mentorship.pending ?? 0} awaiting your response`}
          icon={<Users />}
          tone="success"
        />
        <Stat
          label="Research calls"
          value={data.research.open_projects ?? 0}
          sublabel="Open to applications"
          icon={<FlaskConical />}
          tone="ink"
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Profile completeness</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Progress value={data.profile_completion} showValue label="Complete" />
            <p className="text-sm leading-relaxed text-ink-600">
              A complete profile — specialisation, research areas and experience —
              is what lets us match you to the right industry programmes and
              students.
            </p>
            <Link href="/academician/profile">
              <Button variant="secondary" size="sm" block>Update profile</Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-start justify-between gap-3">
            <div>
              <CardTitle>Programmes matched to your expertise</CardTitle>
              <p className="mt-1 text-sm text-ink-500">
                Filtered by your research areas and eligibility
              </p>
            </div>
            <Link href="/academician/opportunities">
              <Button variant="secondary" size="sm">See all</Button>
            </Link>
          </CardHeader>
          <CardContent>
            {data.recommended_opportunities.length === 0 ? (
              <EmptyState
                className="border-0 bg-transparent py-6"
                icon={<Briefcase />}
                title="No matched programmes yet"
                description="Add your research and expertise areas, and matching programmes will appear here."
                action={
                  <Link href="/academician/profile">
                    <Button size="sm">Complete your profile</Button>
                  </Link>
                }
              />
            ) : (
              <ul className="space-y-3">
                {data.recommended_opportunities.map((item) => (
                  <li key={item.id}>
                    <Link
                      href={`/opportunities/${item.id}`}
                      className="block rounded-xl border border-ink-200 p-4 transition-colors hover:border-ink-300 hover:bg-surface-muted"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-ink-900">
                            {item.title}
                          </p>
                          <p className="truncate text-xs text-ink-500">
                            {item.company_name}
                            {item.deadline ? ` · closes ${formatDate(item.deadline)}` : ""}
                          </p>
                        </div>
                        <Badge tone="brand">
                          {item.kind.replace(/_/g, " ").toLowerCase()}
                        </Badge>
                      </div>
                      <ul className="mt-2 space-y-0.5">
                        {item.reasons.map((reason) => (
                          <li key={reason} className="text-xs text-ink-600">
                            • {reason}
                          </li>
                        ))}
                      </ul>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-3">
            <CardTitle>Upcoming mentorship sessions</CardTitle>
            <Link href="/academician/mentorship">
              <Button variant="secondary" size="sm">Manage</Button>
            </Link>
          </CardHeader>
          <CardContent>
            {data.upcoming_sessions.length === 0 ? (
              <EmptyState
                className="border-0 bg-transparent py-6"
                icon={<Calendar />}
                title="No sessions scheduled"
                description="Accept a mentorship request and schedule a session to see it here."
              />
            ) : (
              <ul className="divide-y divide-ink-100">
                {data.upcoming_sessions.map((session) => (
                  <li key={session.id} className="flex items-center gap-3 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-ink-900">
                        {session.agenda || "Mentorship session"}
                      </p>
                      <p className="text-xs text-ink-500">
                        {formatDateTime(session.scheduled_at)} · {session.duration_minutes} min
                      </p>
                    </div>
                    {session.meeting_link && (
                      <a href={session.meeting_link} target="_blank" rel="noreferrer">
                        <Button size="sm" variant="secondary">Join</Button>
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-start justify-between gap-3">
            <CardTitle>My applications</CardTitle>
            <Link href="/academician/research">
              <Button variant="secondary" size="sm">Research</Button>
            </Link>
          </CardHeader>
          <CardContent>
            {totalApplications === 0 ? (
              <EmptyState
                className="border-0 bg-transparent py-6"
                icon={<Award />}
                title="No applications yet"
                description="Apply to a faculty programme or a research call to track it here."
              />
            ) : (
              <ul className="space-y-2">
                {Object.entries(data.my_applications).map(([status, count]) => (
                  <li
                    key={status}
                    className="flex items-center justify-between rounded-lg bg-surface-muted px-3 py-2"
                  >
                    <span className="text-sm capitalize text-ink-700">
                      {status.replace(/_/g, " ").toLowerCase()}
                    </span>
                    <Badge tone="neutral">{count}</Badge>
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
