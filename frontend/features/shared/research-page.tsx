"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Calendar, FlaskConical, Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input, Select, Textarea } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { Paged } from "@/types/api";

interface ResearchProject {
  id: string;
  title: string;
  abstract: string;
  project_type: string;
  status: string;
  company?: { name: string } | null;
  research_areas: string[];
  funding_amount?: number | null;
  duration_months?: number | null;
  application_deadline?: string | null;
  positions: number;
  application_count: number;
  has_applied: boolean;
}

interface ResearchApplication {
  id: string;
  project_id: string;
  project?: ResearchProject | null;
  academician_name: string;
  proposal: string;
  status: string;
  created_at: string;
}

export function ResearchPage({ mode }: { mode: "academician" | "industry" }) {
  const queryClient = useQueryClient();
  const [type, setType] = useState("");
  const [applyTo, setApplyTo] = useState<ResearchProject | null>(null);
  const [proposal, setProposal] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({
    title: "", abstract: "", project_type: "RESEARCH", funding_amount: "",
    duration_months: "", positions: 1,
  });

  const projects = useQuery({
    queryKey: ["research", "projects", type],
    queryFn: () =>
      api.paged<ResearchProject>("/research/projects", {
        project_type: type || undefined,
        page_size: 24,
      }) as Promise<Paged<ResearchProject>>,
  });

  const myApplications = useQuery({
    queryKey: ["research", "applications"],
    queryFn: () =>
      api.paged<ResearchApplication>("/research/applications/mine", {
        page_size: 30,
      }) as Promise<Paged<ResearchApplication>>,
    enabled: mode === "academician",
  });

  const apply = useMutation({
    mutationFn: (projectId: string) =>
      api.post(`/research/projects/${projectId}/apply`, { proposal }),
    onSuccess: () => {
      toast.success("Proposal submitted");
      setApplyTo(null);
      setProposal("");
      void queryClient.invalidateQueries({ queryKey: ["research"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not apply"),
  });

  const create = useMutation({
    mutationFn: () =>
      api.post("/research/projects", {
        title: form.title,
        abstract: form.abstract,
        project_type: form.project_type,
        funding_amount: form.funding_amount ? Number(form.funding_amount) : undefined,
        duration_months: form.duration_months ? Number(form.duration_months) : undefined,
        positions: Number(form.positions),
      }),
    onSuccess: () => {
      toast.success("Collaboration published");
      setCreateOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["research"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not publish"),
  });

  return (
    <>
      <PageHeader
        title="Research & consultancy"
        description={
          mode === "academician"
            ? "Industry-funded research, consultancy engagements and joint publications open to faculty."
            : "Research and consultancy calls published by your company, and the proposals received."
        }
        actions={
          mode === "industry" && (
            <Button onClick={() => setCreateOpen(true)} leftIcon={<Plus />}>
              Publish a call
            </Button>
          )
        }
      />

      <Tabs defaultValue="open">
        <TabsList ariaLabel="Research views">
          <TabsTrigger value="open">
            {mode === "industry" ? "Published calls" : "Open calls"}
          </TabsTrigger>
          {mode === "academician" && (
            <TabsTrigger value="mine">
              My proposals
              {myApplications.data?.meta.total ? ` (${myApplications.data.meta.total})` : ""}
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="open">
          <div className="mb-4 max-w-xs">
            <Select
              label="Type"
              value={type}
              onChange={(event) => setType(event.target.value)}
            >
              <option value="">All types</option>
              {["RESEARCH", "CONSULTANCY", "JOINT_PUBLICATION", "INNOVATION", "SPONSORED_RESEARCH"].map(
                (item) => (
                  <option key={item} value={item}>
                    {item.replace(/_/g, " ").toLowerCase()}
                  </option>
                ),
              )}
            </Select>
          </div>

          {projects.isLoading && <SkeletonList count={4} rows={3} />}
          {projects.error && (
            <ErrorState error={projects.error} onRetry={() => void projects.refetch()} />
          )}
          {projects.data?.data.length === 0 && (
            <EmptyState
              icon={<FlaskConical />}
              title="No open collaborations"
              description={
                mode === "industry"
                  ? "Publish a research or consultancy call to reach faculty across partner institutions."
                  : "Research and consultancy calls from industry will appear here."
              }
            />
          )}

          <div className="grid gap-4 md:grid-cols-2">
            {projects.data?.data.map((project) => (
              <Card key={project.id} className="flex flex-col p-5">
                <div className="flex flex-wrap gap-1.5">
                  <Badge tone="brand">
                    {project.project_type.replace(/_/g, " ").toLowerCase()}
                  </Badge>
                  <Badge tone="outline">{project.status.toLowerCase()}</Badge>
                </div>
                <h3 className="mt-2 text-[15px] font-semibold text-ink-900">
                  {project.title}
                </h3>
                <p className="flex items-center gap-1.5 text-xs text-ink-500">
                  <Building2 className="size-3.5 text-ink-400" aria-hidden />
                  {project.company?.name ?? "—"}
                </p>
                <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-ink-600">
                  {project.abstract}
                </p>

                {project.research_areas.length > 0 && (
                  <div className="mt-2.5 flex flex-wrap gap-1">
                    {project.research_areas.slice(0, 4).map((area) => (
                      <Badge key={area} tone="neutral">{area}</Badge>
                    ))}
                  </div>
                )}

                <dl className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-600">
                  {project.funding_amount ? (
                    <div><dd>{formatCurrency(project.funding_amount)} funding</dd></div>
                  ) : null}
                  {project.duration_months ? (
                    <div><dd>{project.duration_months} months</dd></div>
                  ) : null}
                  {project.application_deadline && (
                    <div className="flex items-center gap-1">
                      <Calendar className="size-3.5 text-ink-400" aria-hidden />
                      <dd>{formatDate(project.application_deadline)}</dd>
                    </div>
                  )}
                </dl>

                <div className="mt-auto flex items-center justify-between gap-2 border-t border-ink-100 pt-3.5 mt-4">
                  <span className="text-xs text-ink-500">
                    {project.application_count} proposal
                    {project.application_count === 1 ? "" : "s"}
                  </span>
                  {mode === "academician" && (
                    <Button
                      size="sm"
                      disabled={project.has_applied}
                      onClick={() => {
                        setApplyTo(project);
                        setProposal("");
                      }}
                    >
                      {project.has_applied ? "Applied" : "Submit proposal"}
                    </Button>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </TabsContent>

        {mode === "academician" && (
          <TabsContent value="mine">
            {myApplications.isLoading && <SkeletonList count={3} rows={2} />}
            {myApplications.data?.data.length === 0 && (
              <EmptyState
                icon={<FlaskConical />}
                title="No proposals submitted"
                description="Submit a proposal to an open call and track it here."
              />
            )}
            <div className="space-y-3">
              {myApplications.data?.data.map((application) => (
                <Card key={application.id} className="p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-ink-900">
                        {application.project?.title}
                      </p>
                      <p className="text-xs text-ink-500">
                        Submitted {formatDate(application.created_at)}
                      </p>
                    </div>
                    <Badge
                      tone={
                        application.status === "ACCEPTED"
                          ? "success"
                          : application.status === "REJECTED"
                            ? "danger"
                            : "brand"
                      }
                      size="md"
                    >
                      {application.status.replace(/_/g, " ").toLowerCase()}
                    </Badge>
                  </div>
                  <p className="mt-2 line-clamp-2 text-sm text-ink-600">
                    {application.proposal}
                  </p>
                </Card>
              ))}
            </div>
          </TabsContent>
        )}
      </Tabs>

      {applyTo && (
        <Dialog
          open
          onClose={() => setApplyTo(null)}
          title={`Proposal: ${applyTo.title}`}
          description="Describe your relevant expertise and what you would contribute."
          size="lg"
          footer={
            <>
              <Button variant="secondary" onClick={() => setApplyTo(null)}>Cancel</Button>
              <Button
                disabled={proposal.trim().length < 20}
                isLoading={apply.isPending}
                onClick={() => apply.mutate(applyTo.id)}
              >
                Submit proposal
              </Button>
            </>
          }
        >
          <Textarea
            label="Your proposal"
            rows={8}
            required
            hint={`${proposal.length} characters — at least 20 needed`}
            value={proposal}
            onChange={(event) => setProposal(event.target.value)}
          />
        </Dialog>
      )}

      {createOpen && (
        <Dialog
          open
          onClose={() => setCreateOpen(false)}
          title="Publish a research or consultancy call"
          size="lg"
          footer={
            <>
              <Button variant="secondary" onClick={() => setCreateOpen(false)}>Cancel</Button>
              <Button
                disabled={form.title.length < 5 || form.abstract.length < 20}
                isLoading={create.isPending}
                onClick={() => create.mutate()}
              >
                Publish
              </Button>
            </>
          }
        >
          <div className="space-y-3">
            <Input
              label="Title"
              required
              value={form.title}
              onChange={(event) => setForm((c) => ({ ...c, title: event.target.value }))}
            />
            <Textarea
              label="Abstract"
              rows={5}
              required
              value={form.abstract}
              onChange={(event) => setForm((c) => ({ ...c, abstract: event.target.value }))}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <Select
                label="Type"
                value={form.project_type}
                onChange={(event) =>
                  setForm((c) => ({ ...c, project_type: event.target.value }))
                }
              >
                {["RESEARCH", "CONSULTANCY", "JOINT_PUBLICATION", "INNOVATION", "SPONSORED_RESEARCH"].map(
                  (item) => (
                    <option key={item} value={item}>
                      {item.replace(/_/g, " ").toLowerCase()}
                    </option>
                  ),
                )}
              </Select>
              <Input
                label="Positions"
                type="number"
                min={1}
                value={form.positions}
                onChange={(event) =>
                  setForm((c) => ({ ...c, positions: Number(event.target.value) }))
                }
              />
              <Input
                label="Funding amount"
                type="number"
                min={0}
                value={form.funding_amount}
                onChange={(event) =>
                  setForm((c) => ({ ...c, funding_amount: event.target.value }))
                }
              />
              <Input
                label="Duration (months)"
                type="number"
                min={1}
                value={form.duration_months}
                onChange={(event) =>
                  setForm((c) => ({ ...c, duration_months: event.target.value }))
                }
              />
            </div>
          </div>
        </Dialog>
      )}
    </>
  );
}
