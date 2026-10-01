"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, Download, ExternalLink, Search, Users } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { TBody, TD, TH, THead, TR, Table, TableWrapper } from "@/components/ui/table";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, ApiError, downloadFile } from "@/lib/api";
import type { Paged } from "@/types/api";

interface StudentSummary {
  id: string;
  user_id: string;
  full_name: string;
  headline?: string | null;
  avatar_url?: string | null;
  city?: string | null;
  institution_name?: string | null;
  department_name?: string | null;
  degree?: string | null;
  graduation_year?: number | null;
  cgpa?: number | null;
  skill_readiness_score: number;
  profile_completion: number;
  is_placed: boolean;
  is_open_to_work: boolean;
  top_skills: string[];
  portfolio_slug?: string | null;
}

export function InstitutionStudents() {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [graduationYear, setGraduationYear] = useState("");
  const [placed, setPlaced] = useState("");
  const [minReadiness, setMinReadiness] = useState("");
  const [page, setPage] = useState(1);

  const students = useQuery({
    queryKey: ["institution", "students", { search, graduationYear, placed, minReadiness, page }],
    queryFn: () =>
      api.paged<StudentSummary>("/institutions/me/students", {
        q: search || undefined,
        graduation_year: graduationYear || undefined,
        is_placed: placed === "" ? undefined : placed === "true",
        min_readiness: minReadiness || undefined,
        page,
        page_size: 25,
      }) as Promise<Paged<StudentSummary>>,
  });

  const verify = useMutation({
    mutationFn: (studentId: string) =>
      api.post<{ message: string }>(`/institutions/me/students/${studentId}/verify`),
    onSuccess: (result) => {
      toast.success(result.message ?? "Credentials verified");
      void queryClient.invalidateQueries({ queryKey: ["institution"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not verify"),
  });

  const exportCsv = async () => {
    try {
      await downloadFile(
        "/analytics/reports/student-readiness",
        "student-readiness.csv",
        { format: "csv" },
      );
      toast.success("Downloaded");
    } catch {
      toast.error("Could not export");
    }
  };

  return (
    <>
      <PageHeader
        title="Students"
        description="Your cohort, their measured readiness and placement status."
        actions={
          <Button variant="secondary" leftIcon={<Download />} onClick={() => void exportCsv()}>
            Export CSV
          </Button>
        }
      />

      <Card className="mb-5 p-4">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setSearch(query);
            setPage(1);
          }}
          className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"
        >
          <Input
            label="Search"
            leftIcon={<Search />}
            placeholder="Student name"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <Input
            label="Graduation year"
            type="number"
            placeholder="2027"
            value={graduationYear}
            onChange={(event) => {
              setGraduationYear(event.target.value);
              setPage(1);
            }}
          />
          <Select
            label="Placement"
            value={placed}
            onChange={(event) => {
              setPlaced(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All</option>
            <option value="true">Placed</option>
            <option value="false">Not placed</option>
          </Select>
          <Select
            label="Minimum readiness"
            value={minReadiness}
            onChange={(event) => {
              setMinReadiness(event.target.value);
              setPage(1);
            }}
          >
            <option value="">Any</option>
            <option value="40">40%+</option>
            <option value="60">60%+</option>
            <option value="80">80%+</option>
          </Select>
          <div className="flex items-end">
            <Button type="submit" block>Filter</Button>
          </div>
        </form>
      </Card>

      {students.isLoading && <SkeletonList count={4} rows={2} />}
      {students.error && (
        <ErrorState error={students.error} onRetry={() => void students.refetch()} />
      )}
      {students.data?.data.length === 0 && (
        <EmptyState
          icon={<Users />}
          title="No students match"
          description="Try clearing the filters, or check that students have registered with your institution."
        />
      )}

      {students.data && students.data.data.length > 0 && (
        <>
          <p className="mb-3 text-sm text-ink-500">
            {students.data.meta.total} student{students.data.meta.total === 1 ? "" : "s"}
          </p>
          <TableWrapper caption="Students">
            <Table>
              <THead>
                <TR>
                  <TH>Student</TH>
                  <TH>Programme</TH>
                  <TH>CGPA</TH>
                  <TH>Readiness</TH>
                  <TH>Profile</TH>
                  <TH>Status</TH>
                  <TH><span className="sr-only">Actions</span></TH>
                </TR>
              </THead>
              <TBody>
                {students.data.data.map((student) => (
                  <TR key={student.id}>
                    <TD>
                      <div className="flex items-center gap-2.5">
                        <Avatar name={student.full_name} src={student.avatar_url} size="sm" />
                        <div className="min-w-0">
                          <p className="truncate font-medium text-ink-900">
                            {student.full_name}
                          </p>
                          <p className="truncate text-2xs text-ink-500">
                            {student.top_skills.slice(0, 3).join(" · ") || "No skills yet"}
                          </p>
                        </div>
                      </div>
                    </TD>
                    <TD className="whitespace-nowrap text-xs">
                      {student.department_name ?? "—"}
                      <br />
                      <span className="text-ink-500">{student.graduation_year ?? "—"}</span>
                    </TD>
                    <TD className="tabular-nums">{student.cgpa ?? "—"}</TD>
                    <TD>
                      <div className="w-24">
                        <Progress value={student.skill_readiness_score} size="sm" showValue />
                      </div>
                    </TD>
                    <TD>
                      <div className="w-20">
                        <Progress
                          value={student.profile_completion}
                          size="sm"
                          tone="ink"
                        />
                      </div>
                    </TD>
                    <TD>
                      <Badge tone={student.is_placed ? "success" : "neutral"}>
                        {student.is_placed ? "Placed" : "Seeking"}
                      </Badge>
                    </TD>
                    <TD>
                      <div className="flex justify-end gap-1">
                        {student.portfolio_slug && (
                          <Link href={`/portfolio/${student.portfolio_slug}`} target="_blank">
                            <Button size="sm" variant="ghost" aria-label="View portfolio">
                              <ExternalLink />
                            </Button>
                          </Link>
                        )}
                        <Button
                          size="sm"
                          variant="secondary"
                          leftIcon={<BadgeCheck />}
                          isLoading={verify.isPending && verify.variables === student.id}
                          onClick={() => verify.mutate(student.id)}
                        >
                          Verify
                        </Button>
                      </div>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </TableWrapper>

          {students.data.meta.total_pages > 1 && (
            <nav className="mt-4 flex items-center justify-center gap-2" aria-label="Pagination">
              <Button
                variant="secondary"
                size="sm"
                disabled={!students.data.meta.has_previous}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="px-2 text-sm text-ink-600">
                Page {students.data.meta.page} of {students.data.meta.total_pages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={!students.data.meta.has_next}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </nav>
          )}
        </>
      )}
    </>
  );
}
