"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Award, BarChart3, Building2, Download, GraduationCap, TrendingUp, Users,
} from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import {
  BarChartCard, DonutChartCard, LineChartCard,
} from "@/components/charts/charts";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Stat } from "@/components/ui/stat";
import { TBody, TD, TH, THead, TR, Table, TableWrapper } from "@/components/ui/table";
import { EmptyState, ErrorState, SkeletonStats } from "@/components/ui/states";
import { api, downloadFile } from "@/lib/api";

interface InstitutionAnalytics {
  summary: {
    total_students: number;
    placed_students: number;
    placement_rate: number;
    average_readiness: number;
    average_profile_completion: number;
    total_applications: number;
    internship_participants: number;
    internship_participation_rate: number;
    internships_secured: number;
    industry_partnerships: number;
    certifications_earned: number;
    assessments_completed: number;
    learning_enrolments: number;
  };
  applications_by_status: Record<string, number>;
  readiness_distribution: Record<string, number>;
  top_skills: { skill: string; students: number }[];
  skill_gaps: { skill: string; students_affected: number }[];
  demand_vs_supply: {
    skill: string;
    industry_demand: number;
    student_supply: number;
    coverage_percentage: number;
    shortfall: number;
  }[];
  departments: {
    department: string;
    students: number;
    average_readiness: number;
    placed: number;
    placement_rate: number;
  }[];
  trends: {
    months: string[];
    applications: number[];
    internships: number[];
    placements: number[];
  };
  top_hiring_companies: { company: string; applications: number }[];
}

export function InstitutionDashboard() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["institution", "analytics"],
    queryFn: () => api.get<InstitutionAnalytics>("/analytics/institution"),
  });

  const exportReport = async (report: string, format: "csv" | "pdf") => {
    try {
      await downloadFile(
        `/analytics/reports/${report}`,
        `skillbridge-${report}.${format}`,
        { format },
      );
      toast.success(`${report} report downloaded`);
    } catch {
      toast.error("Could not generate the report");
    }
  };

  if (isLoading) {
    return (
      <>
        <PageHeader title="Institution dashboard" />
        <SkeletonStats />
      </>
    );
  }
  if (error || !data) {
    return (
      <>
        <PageHeader title="Institution dashboard" />
        <ErrorState error={error} onRetry={() => void refetch()} />
      </>
    );
  }

  const { summary, trends } = data;
  const trendData = trends.months.map((month, index) => ({
    month: month.slice(5),
    applications: trends.applications[index],
    internships: trends.internships[index],
    placements: trends.placements[index],
  }));

  const readinessData = Object.entries(data.readiness_distribution).map(
    ([band, count]) => ({ name: `${band}%`, value: count }),
  );

  return (
    <>
      <PageHeader
        title="Institution dashboard"
        description="Cohort readiness, placement performance, and how your students' skills compare with live industry demand."
        actions={
          <>
            <Button
              variant="secondary"
              leftIcon={<Download />}
              onClick={() => void exportReport("student-readiness", "csv")}
            >
              Export CSV
            </Button>
            <Button
              leftIcon={<Download />}
              onClick={() => void exportReport("placement", "pdf")}
            >
              Placement report
            </Button>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Students"
          value={summary.total_students}
          sublabel={`${summary.average_profile_completion}% average profile completion`}
          icon={<Users />}
          tone="brand"
        />
        <Stat
          label="Average readiness"
          value={`${summary.average_readiness}%`}
          sublabel="Against each student's target role"
          icon={<TrendingUp />}
          tone="success"
        />
        <Stat
          label="Placement rate"
          value={`${summary.placement_rate}%`}
          sublabel={`${summary.placed_students} placed`}
          icon={<GraduationCap />}
          tone="accent"
        />
        <Stat
          label="Industry partners"
          value={summary.industry_partnerships}
          sublabel={`${summary.internship_participation_rate}% doing internships`}
          icon={<Building2 />}
          tone="ink"
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Twelve-month trend</CardTitle>
            <p className="text-sm text-ink-500">
              Applications, internships secured and placements
            </p>
          </CardHeader>
          <CardContent>
            <LineChartCard
              data={trendData}
              xKey="month"
              area
              lines={[
                { key: "applications", name: "Applications" },
                { key: "internships", name: "Internships" },
                { key: "placements", name: "Placements" },
              ]}
              emptyLabel="No activity recorded yet"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Readiness distribution</CardTitle>
            <p className="text-sm text-ink-500">How the cohort is spread</p>
          </CardHeader>
          <CardContent>
            <DonutChartCard data={readinessData} emptyLabel="No readiness data yet" />
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Industry demand vs student supply</CardTitle>
          <p className="text-sm text-ink-500">
            Skills employers are asking for on the platform, against how many of
            your students can evidence them. The largest shortfalls are where
            curriculum or training investment pays back fastest.
          </p>
        </CardHeader>
        <CardContent>
          {data.demand_vs_supply.length === 0 ? (
            <EmptyState
              className="border-0 bg-transparent"
              title="Not enough data yet"
              description="This fills in as employers publish postings and students build skill profiles."
            />
          ) : (
            <TableWrapper caption="Demand versus supply">
              <Table>
                <THead>
                  <TR>
                    <TH>Skill</TH>
                    <TH>Industry demand</TH>
                    <TH>Students with it</TH>
                    <TH>Cohort coverage</TH>
                    <TH>Shortfall</TH>
                  </TR>
                </THead>
                <TBody>
                  {data.demand_vs_supply.slice(0, 12).map((row) => (
                    <TR key={row.skill}>
                      <TD className="font-medium text-ink-900">{row.skill}</TD>
                      <TD className="tabular-nums">{row.industry_demand} postings</TD>
                      <TD className="tabular-nums">{row.student_supply}</TD>
                      <TD>
                        <div className="w-28">
                          <Progress
                            value={row.coverage_percentage}
                            size="sm"
                            showValue
                            tone={row.coverage_percentage < 30 ? "danger" : undefined}
                          />
                        </div>
                      </TD>
                      <TD>
                        <Badge tone={row.shortfall > 10 ? "danger" : row.shortfall > 3 ? "warning" : "neutral"}>
                          {row.shortfall}
                        </Badge>
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </TableWrapper>
          )}
        </CardContent>
      </Card>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Most common skill gaps</CardTitle>
            <p className="text-sm text-ink-500">Across every student&rsquo;s target role</p>
          </CardHeader>
          <CardContent>
            <BarChartCard
              data={data.skill_gaps.slice(0, 8)}
              xKey="skill"
              bars={[{ key: "students_affected", name: "Students affected" }]}
              layout="vertical"
              height={280}
              emptyLabel="No gap analyses run yet"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Performance by department</CardTitle>
          </CardHeader>
          <CardContent>
            {data.departments.length === 0 ? (
              <EmptyState
                className="border-0 bg-transparent"
                title="No department data"
                description="Assign students to departments to see this breakdown."
              />
            ) : (
              <ul className="divide-y divide-ink-100">
                {data.departments.map((department) => (
                  <li key={department.department} className="py-3">
                    <div className="flex items-baseline justify-between gap-2">
                      <p className="truncate text-sm font-medium text-ink-900">
                        {department.department}
                      </p>
                      <span className="shrink-0 text-xs text-ink-500">
                        {department.students} students · {department.placement_rate}% placed
                      </span>
                    </div>
                    <div className="mt-1.5">
                      <Progress
                        value={department.average_readiness}
                        size="sm"
                        label="Average readiness"
                        showValue
                      />
                    </div>
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
            <CardTitle>Top hiring companies</CardTitle>
            <Link href="/institution/partnerships">
              <Button variant="secondary" size="sm">Partnerships</Button>
            </Link>
          </CardHeader>
          <CardContent>
            {data.top_hiring_companies.length === 0 ? (
              <EmptyState
                className="border-0 bg-transparent"
                title="No applications yet"
                description="Company engagement appears here once students start applying."
              />
            ) : (
              <ul className="divide-y divide-ink-100">
                {data.top_hiring_companies.map((company) => (
                  <li
                    key={company.company}
                    className="flex items-center justify-between py-2.5"
                  >
                    <span className="truncate text-sm text-ink-800">{company.company}</span>
                    <Badge tone="brand">{company.applications} applications</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Engagement</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-4">
              {[
                ["Assessments completed", summary.assessments_completed, <Award key="a" />],
                ["Certifications earned", summary.certifications_earned, <GraduationCap key="c" />],
                ["Learning enrolments", summary.learning_enrolments, <BarChart3 key="l" />],
                ["Total applications", summary.total_applications, <TrendingUp key="t" />],
              ].map(([label, value, icon]) => (
                <div key={label as string} className="rounded-xl bg-surface-muted p-4">
                  <span className="flex size-8 items-center justify-center rounded-lg bg-surface text-ink-500 [&_svg]:size-4">
                    {icon as React.ReactNode}
                  </span>
                  <dd className="mt-2 text-xl font-semibold tabular-nums text-ink-900">
                    {value as number}
                  </dd>
                  <dt className="text-xs text-ink-500">{label as string}</dt>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
