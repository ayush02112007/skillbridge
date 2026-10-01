"use client";

/**
 * Institution sub-pages that are all "a filtered view of the institution's own
 * data": placements, internships, departments and partnerships. One component
 * serves them so the behaviour and empty states stay consistent.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Briefcase, GraduationCap, Plus, Users } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { TBody, TD, TH, THead, TR, Table, TableWrapper } from "@/components/ui/table";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import type { Paged } from "@/types/api";

interface Department {
  id: string;
  name: string;
  code: string;
  hod_name?: string | null;
  student_count: number;
}

interface Partnership {
  id: string;
  company_id: string;
  company_name: string;
  partnership_type: string;
  status: string;
  summary: string;
  started_on?: string | null;
  engagement_score: number;
}

interface InstitutionAnalytics {
  summary: Record<string, number>;
  departments: {
    department: string;
    students: number;
    average_readiness: number;
    placed: number;
    placement_rate: number;
  }[];
  top_hiring_companies: { company: string; applications: number }[];
}

export function Departments() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", code: "", hod_name: "" });

  const departments = useQuery({
    queryKey: ["institution", "departments"],
    queryFn: () => api.get<Department[]>("/institutions/me/departments"),
  });

  const create = useMutation({
    mutationFn: () =>
      api.post<Department>("/institutions/me/departments", {
        name: form.name,
        code: form.code.toUpperCase(),
        hod_name: form.hod_name || undefined,
      }),
    onSuccess: () => {
      toast.success("Department created");
      setOpen(false);
      setForm({ name: "", code: "", hod_name: "" });
      void queryClient.invalidateQueries({ queryKey: ["institution"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not create"),
  });

  return (
    <>
      <PageHeader
        title="Departments"
        description="Departments let you break readiness and placement analytics down by cohort."
        actions={
          <Button onClick={() => setOpen(true)} leftIcon={<Plus />}>
            Add department
          </Button>
        }
      />

      {departments.isLoading && <SkeletonList count={3} rows={1} />}
      {departments.error && (
        <ErrorState error={departments.error} onRetry={() => void departments.refetch()} />
      )}
      {departments.data?.length === 0 && (
        <EmptyState
          icon={<Building2 />}
          title="No departments yet"
          description="Add your departments so students can be grouped and compared."
          action={
            <Button size="sm" onClick={() => setOpen(true)} leftIcon={<Plus />}>
              Add the first
            </Button>
          }
        />
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {departments.data?.map((department) => (
          <Card key={department.id} className="p-5">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-[15px] font-semibold text-ink-900">
                  {department.name}
                </p>
                <p className="text-xs text-ink-500">{department.hod_name ?? "No HoD set"}</p>
              </div>
              <Badge tone="brand">{department.code}</Badge>
            </div>
            <p className="mt-3 flex items-center gap-1.5 text-sm text-ink-600">
              <Users className="size-4 text-ink-400" aria-hidden />
              {department.student_count} student{department.student_count === 1 ? "" : "s"}
            </p>
          </Card>
        ))}
      </div>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Add a department"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button
              disabled={!form.name || !form.code}
              isLoading={create.isPending}
              onClick={() => create.mutate()}
            >
              Create
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Input
            label="Department name"
            required
            placeholder="Computer Engineering"
            value={form.name}
            onChange={(event) => setForm((c) => ({ ...c, name: event.target.value }))}
          />
          <Input
            label="Code"
            required
            placeholder="CSE"
            value={form.code}
            onChange={(event) => setForm((c) => ({ ...c, code: event.target.value }))}
          />
          <Input
            label="Head of department"
            value={form.hod_name}
            onChange={(event) => setForm((c) => ({ ...c, hod_name: event.target.value }))}
          />
        </div>
      </Dialog>
    </>
  );
}

export function Partnerships() {
  const partnerships = useQuery({
    queryKey: ["institution", "partnerships"],
    queryFn: () => api.get<Partnership[]>("/institutions/me/partnerships"),
  });

  const analytics = useQuery({
    queryKey: ["institution", "analytics"],
    queryFn: () => api.get<InstitutionAnalytics>("/analytics/institution"),
  });

  return (
    <>
      <PageHeader
        title="Industry partners"
        description="Formal partnerships, and the companies actually engaging with your students."
      />

      {partnerships.isLoading && <SkeletonList count={3} rows={1} />}
      {partnerships.error && (
        <ErrorState error={partnerships.error} onRetry={() => void partnerships.refetch()} />
      )}
      {partnerships.data?.length === 0 && (
        <EmptyState
          icon={<Building2 />}
          title="No partnerships recorded"
          description="Partnerships appear here once they are established on the platform."
        />
      )}

      {partnerships.data && partnerships.data.length > 0 && (
        <TableWrapper caption="Industry partnerships">
          <Table>
            <THead>
              <TR>
                <TH>Company</TH>
                <TH>Type</TH>
                <TH>Status</TH>
                <TH>Since</TH>
                <TH>Engagement</TH>
              </TR>
            </THead>
            <TBody>
              {partnerships.data.map((partnership) => (
                <TR key={partnership.id}>
                  <TD>
                    <p className="font-medium text-ink-900">{partnership.company_name}</p>
                    <p className="max-w-md truncate text-2xs text-ink-500">
                      {partnership.summary}
                    </p>
                  </TD>
                  <TD>
                    <Badge tone="outline">
                      {partnership.partnership_type.toLowerCase()}
                    </Badge>
                  </TD>
                  <TD>
                    <Badge tone={partnership.status === "ACTIVE" ? "success" : "neutral"}>
                      {partnership.status.toLowerCase()}
                    </Badge>
                  </TD>
                  <TD className="whitespace-nowrap text-xs">
                    {partnership.started_on ?? "—"}
                  </TD>
                  <TD>
                    <div className="w-24">
                      <Progress value={partnership.engagement_score} size="sm" showValue />
                    </div>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </TableWrapper>
      )}

      {analytics.data && analytics.data.top_hiring_companies.length > 0 && (
        <Card className="mt-6 p-5">
          <h2 className="text-base font-semibold text-ink-900">
            Companies hiring from you
          </h2>
          <p className="mt-0.5 text-sm text-ink-500">
            Measured from actual applications, regardless of formal partnership.
          </p>
          <ul className="mt-3 divide-y divide-ink-100">
            {analytics.data.top_hiring_companies.map((company) => (
              <li
                key={company.company}
                className="flex items-center justify-between py-2.5"
              >
                <span className="text-sm text-ink-800">{company.company}</span>
                <Badge tone="brand">{company.applications} applications</Badge>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}

export function PlacementsView({ mode }: { mode: "placement" | "internship" }) {
  const analytics = useQuery({
    queryKey: ["institution", "analytics"],
    queryFn: () => api.get<InstitutionAnalytics>("/analytics/institution"),
  });

  const summary = analytics.data?.summary;

  return (
    <>
      <PageHeader
        title={mode === "placement" ? "Placements" : "Internships"}
        description={
          mode === "placement"
            ? "Placement performance across the cohort, by department."
            : "Internship participation and conversion across the cohort."
        }
      />

      {analytics.isLoading && <SkeletonList count={2} rows={3} />}
      {analytics.error && (
        <ErrorState error={analytics.error} onRetry={() => void analytics.refetch()} />
      )}

      {summary && (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {(mode === "placement"
              ? ([
                  ["Students", summary.total_students, <Users key="u" />],
                  ["Placed", summary.placed_students, <GraduationCap key="g" />],
                  ["Placement rate", `${summary.placement_rate}%`, <Briefcase key="b" />],
                  ["Applications", summary.total_applications, <Briefcase key="a" />],
                ] as const)
              : ([
                  ["Students", summary.total_students, <Users key="u" />],
                  ["Doing internships", summary.internship_participants, <Briefcase key="b" />],
                  [
                    "Participation",
                    `${summary.internship_participation_rate}%`,
                    <GraduationCap key="g" />,
                  ],
                  ["Internships secured", summary.internships_secured, <Briefcase key="i" />],
                ] as const)
            ).map(([label, value, icon]) => (
              <Card key={label} className="p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-ink-500">{label}</p>
                    <p className="mt-1 text-2xl font-semibold tabular-nums text-ink-900">
                      {value}
                    </p>
                  </div>
                  <span className="flex size-9 items-center justify-center rounded-xl bg-brand-50 text-brand-700 [&_svg]:size-4">
                    {icon}
                  </span>
                </div>
              </Card>
            ))}
          </div>

          {analytics.data && analytics.data.departments.length > 0 ? (
            <TableWrapper caption="By department">
              <Table>
                <THead>
                  <TR>
                    <TH>Department</TH>
                    <TH>Students</TH>
                    <TH>Average readiness</TH>
                    <TH>Placed</TH>
                    <TH>Placement rate</TH>
                  </TR>
                </THead>
                <TBody>
                  {analytics.data.departments.map((department) => (
                    <TR key={department.department}>
                      <TD className="font-medium text-ink-900">{department.department}</TD>
                      <TD className="tabular-nums">{department.students}</TD>
                      <TD>
                        <div className="w-28">
                          <Progress
                            value={department.average_readiness}
                            size="sm"
                            showValue
                          />
                        </div>
                      </TD>
                      <TD className="tabular-nums">{department.placed}</TD>
                      <TD>
                        <Badge
                          tone={
                            department.placement_rate >= 60
                              ? "success"
                              : department.placement_rate >= 30
                                ? "warning"
                                : "neutral"
                          }
                        >
                          {department.placement_rate}%
                        </Badge>
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </TableWrapper>
          ) : (
            <EmptyState
              icon={<Building2 />}
              title="No department breakdown yet"
              description="Assign students to departments to see performance split out."
            />
          )}
        </>
      )}
    </>
  );
}
