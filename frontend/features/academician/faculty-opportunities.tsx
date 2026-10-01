"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Briefcase, Building2, Calendar, MapPin } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { Opportunity, Paged } from "@/types/api";

interface FacultyApplication {
  id: string;
  status: string;
  submitted_at: string;
  opportunity_id: string;
  opportunity_title: string;
  company_name: string;
  kind?: string | null;
}

export function FacultyOpportunities() {
  const queryClient = useQueryClient();
  const [kind, setKind] = useState("");
  const [applyingTo, setApplyingTo] = useState<string | null>(null);

  const opportunities = useQuery({
    queryKey: ["faculty-opportunities", kind],
    queryFn: () =>
      api.paged<Opportunity>("/faculty-opportunities", { page_size: 24 }) as Promise<
        Paged<Opportunity>
      >,
  });

  const applications = useQuery({
    queryKey: ["academician", "applications"],
    queryFn: () => api.get<FacultyApplication[]>("/academicians/applications/mine"),
  });

  const apply = useMutation({
    mutationFn: (id: string) =>
      api.post(`/academicians/faculty-opportunities/${id}/apply`),
    onSuccess: () => {
      toast.success("Application submitted");
      setApplyingTo(null);
      void queryClient.invalidateQueries({ queryKey: ["academician"] });
    },
    onError: (error) => {
      setApplyingTo(null);
      toast.error(error instanceof ApiError ? error.message : "Could not apply");
    },
  });

  const appliedIds = new Set(applications.data?.map((a) => a.opportunity_id) ?? []);
  const filtered = (opportunities.data?.data ?? []).filter((item) => {
    if (!kind) return true;
    const detailKind = (item as unknown as { kind?: string }).kind;
    return detailKind === kind;
  });

  return (
    <>
      <PageHeader
        title="Faculty programmes"
        description="Industry programmes for academicians: faculty internships, FDPs, industrial training, consultancy, research collaboration and guest lectures."
      />

      <Tabs defaultValue="open">
        <TabsList ariaLabel="Programme views">
          <TabsTrigger value="open">Open programmes</TabsTrigger>
          <TabsTrigger value="mine">
            My applications
            {applications.data?.length ? ` (${applications.data.length})` : ""}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="open">
          <div className="mb-4 max-w-xs">
            <Select
              label="Programme type"
              value={kind}
              onChange={(event) => setKind(event.target.value)}
            >
              <option value="">All types</option>
              {[
                "FACULTY_INTERNSHIP", "FDP", "INDUSTRIAL_TRAINING", "CONSULTANCY",
                "RESEARCH_COLLABORATION", "GUEST_LECTURE",
              ].map((item) => (
                <option key={item} value={item}>
                  {item.replace(/_/g, " ").toLowerCase()}
                </option>
              ))}
            </Select>
          </div>

          {opportunities.isLoading && <SkeletonList count={4} rows={3} />}
          {opportunities.error && (
            <ErrorState
              error={opportunities.error}
              onRetry={() => void opportunities.refetch()}
            />
          )}
          {filtered.length === 0 && !opportunities.isLoading && (
            <EmptyState
              icon={<Briefcase />}
              title="No open programmes"
              description="Industry partners publish FDPs, faculty internships and consultancy calls here."
            />
          )}

          <div className="grid gap-4 md:grid-cols-2">
            {filtered.map((item) => {
              const detail = item as unknown as {
                kind?: string;
                duration_days?: number;
                honorarium?: number;
                min_teaching_experience_years?: number;
              };
              const applied = appliedIds.has(item.id);
              return (
                <Card key={item.id} className="flex flex-col p-5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      {detail.kind && (
                        <Badge tone="brand">
                          {detail.kind.replace(/_/g, " ").toLowerCase()}
                        </Badge>
                      )}
                      <h3 className="mt-2 text-[15px] font-semibold text-ink-900">
                        {item.title}
                      </h3>
                      <p className="flex items-center gap-1.5 text-xs text-ink-500">
                        <Building2 className="size-3.5 text-ink-400" aria-hidden />
                        {item.company?.name}
                      </p>
                    </div>
                  </div>

                  <dl className="mt-3 space-y-1 text-xs text-ink-600">
                    <div className="flex items-center gap-1.5">
                      <MapPin className="size-3.5 text-ink-400" aria-hidden />
                      <dd>{item.location_city ?? "—"} · {item.work_mode.toLowerCase()}</dd>
                    </div>
                    {item.application_deadline && (
                      <div className="flex items-center gap-1.5">
                        <Calendar className="size-3.5 text-ink-400" aria-hidden />
                        <dd>Closes {formatDate(item.application_deadline)}</dd>
                      </div>
                    )}
                    {detail.min_teaching_experience_years ? (
                      <div>
                        <dd>
                          Requires {detail.min_teaching_experience_years}+ years of
                          teaching experience
                        </dd>
                      </div>
                    ) : null}
                  </dl>

                  <div className="mt-auto pt-4">
                    <Button
                      block
                      size="sm"
                      disabled={applied}
                      isLoading={apply.isPending && applyingTo === item.id}
                      onClick={() => {
                        setApplyingTo(item.id);
                        apply.mutate(item.id);
                      }}
                    >
                      {applied ? "Applied" : "Apply"}
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="mine">
          {applications.isLoading && <SkeletonList count={3} rows={1} />}
          {applications.data?.length === 0 && (
            <EmptyState
              icon={<Briefcase />}
              title="No applications yet"
              description="Apply to a programme and track it here."
            />
          )}
          <div className="space-y-3">
            {applications.data?.map((application) => (
              <Card
                key={application.id}
                className="flex flex-wrap items-center justify-between gap-3 p-4"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-ink-900">
                    {application.opportunity_title}
                  </p>
                  <p className="text-xs text-ink-500">
                    {application.company_name} · applied{" "}
                    {formatDate(application.submitted_at)}
                  </p>
                </div>
                <Badge tone="brand" size="md">
                  {application.status.replace(/_/g, " ").toLowerCase()}
                </Badge>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </>
  );
}
