"use client";

/**
 * Create and manage postings.
 *
 * The "analyse description" step is the product's answer to recruiters having
 * to tag skills by hand: paste the description, the backend extracts skills by
 * exact taxonomy match, and the recruiter edits the suggestion before it is
 * published. Nothing is added that the text did not contain.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Briefcase, Eye, Plus, Sparkles, Trash2, Wand2,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input, Select, Textarea } from "@/components/ui/input";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { TBody, TD, TH, THead, TR, Table, TableWrapper } from "@/components/ui/table";
import { api, ApiError } from "@/lib/api";
import { formatDate, formatRange } from "@/lib/utils";
import type {
  JobRole, Opportunity, OpportunityStatus, Paged, ProficiencyLevel,
  SkillImportance,
} from "@/types/api";

interface DetectedSkill {
  skill_id: string;
  skill_name: string;
  matched_term: string;
  occurrences: number;
  suggested_level: ProficiencyLevel;
  suggested_importance: SkillImportance;
}

interface AnalysisResult {
  skills: DetectedSkill[];
  keywords: string[];
  responsibilities: string[];
  suggested_job_role_id?: string | null;
  suggested_job_role_title?: string | null;
  extracted_by: string;
}

export interface PostingConfig {
  /** Drives which type-specific fields the create form shows. */
  kind: "internship" | "job" | "project";
  endpoint: "/internships" | "/jobs" | "/projects";
  title: string;
  description: string;
}

export function PostingManager({ config }: { config: PostingConfig }) {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");

  const postings = useQuery({
    queryKey: ["postings", config.endpoint, statusFilter],
    queryFn: () =>
      api.paged<Opportunity>(`${config.endpoint}/mine`, {
        status: statusFilter || undefined,
        page_size: 50,
      }) as Promise<Paged<Opportunity>>,
  });

  const changeStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: OpportunityStatus }) =>
      api.post(`${config.endpoint}/${id}/status`, { status }),
    onSuccess: () => {
      toast.success("Status updated");
      void queryClient.invalidateQueries({ queryKey: ["postings"] });
    },
    onError: (error) => {
      const missing =
        error instanceof ApiError
          ? (error.details as { missing?: string[] } | undefined)?.missing
          : undefined;
      toast.error(error instanceof ApiError ? error.message : "Could not update", {
        description: missing?.join(", "),
      });
    },
  });

  return (
    <>
      <PageHeader
        title={config.title}
        description={config.description}
        actions={
          <Button onClick={() => setCreateOpen(true)} leftIcon={<Plus />}>
            New {config.kind}
          </Button>
        }
      />

      <div className="mb-4 max-w-xs">
        <Select
          label="Status"
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
        >
          <option value="">All</option>
          <option value="DRAFT">Draft</option>
          <option value="PUBLISHED">Published</option>
          <option value="PAUSED">Paused</option>
          <option value="CLOSED">Closed</option>
        </Select>
      </div>

      {postings.isLoading && <SkeletonList count={3} rows={2} />}
      {postings.error && (
        <ErrorState error={postings.error} onRetry={() => void postings.refetch()} />
      )}

      {postings.data?.data.length === 0 && (
        <EmptyState
          icon={<Briefcase />}
          title={`No ${config.kind}s yet`}
          description="Create one, tag the skills it needs, and matched students will find it."
          action={
            <Button size="sm" onClick={() => setCreateOpen(true)} leftIcon={<Plus />}>
              Create your first {config.kind}
            </Button>
          }
        />
      )}

      {postings.data && postings.data.data.length > 0 && (
        <TableWrapper caption={`Your ${config.kind}s`}>
          <Table>
            <THead>
              <TR>
                <TH>Title</TH>
                <TH>Status</TH>
                <TH>Applicants</TH>
                <TH>Views</TH>
                <TH>Compensation</TH>
                <TH>Deadline</TH>
                <TH><span className="sr-only">Actions</span></TH>
              </TR>
            </THead>
            <TBody>
              {postings.data.data.map((posting) => (
                <TR key={posting.id}>
                  <TD>
                    <Link
                      href={`/opportunities/${posting.id}`}
                      className="font-medium text-ink-900 hover:underline"
                    >
                      {posting.title}
                    </Link>
                    <p className="text-xs text-ink-500">
                      {posting.location_city} · {posting.work_mode.toLowerCase()}
                    </p>
                  </TD>
                  <TD>
                    <Badge
                      tone={
                        posting.status === "PUBLISHED"
                          ? "success"
                          : posting.status === "DRAFT"
                            ? "neutral"
                            : "warning"
                      }
                    >
                      {posting.status.toLowerCase()}
                    </Badge>
                  </TD>
                  <TD className="tabular-nums">{posting.applications_count}</TD>
                  <TD className="tabular-nums">{posting.views_count}</TD>
                  <TD className="whitespace-nowrap">
                    {config.kind === "internship"
                      ? formatRange(posting.stipend_min, posting.stipend_max)
                      : config.kind === "project"
                        ? "—"
                        : formatRange(posting.salary_min, posting.salary_max)}
                  </TD>
                  <TD className="whitespace-nowrap">
                    {formatDate(posting.application_deadline)}
                  </TD>
                  <TD>
                    <div className="flex justify-end gap-1">
                      <Link href={`/industry/applicants?opportunity=${posting.id}`}>
                        <Button size="sm" variant="ghost" aria-label="View applicants">
                          <Eye />
                        </Button>
                      </Link>
                      {posting.status === "DRAFT" && (
                        <Button
                          size="sm"
                          onClick={() =>
                            changeStatus.mutate({ id: posting.id, status: "PUBLISHED" })
                          }
                        >
                          Publish
                        </Button>
                      )}
                      {posting.status === "PUBLISHED" && (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() =>
                            changeStatus.mutate({ id: posting.id, status: "CLOSED" })
                          }
                        >
                          Close
                        </Button>
                      )}
                    </div>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </TableWrapper>
      )}

      {createOpen && (
        <CreatePostingDialog
          config={config}
          onClose={() => setCreateOpen(false)}
          onCreated={() => {
            setCreateOpen(false);
            void queryClient.invalidateQueries({ queryKey: ["postings"] });
          }}
        />
      )}
    </>
  );
}

function CreatePostingDialog({
  config,
  onClose,
  onCreated,
}: {
  config: PostingConfig;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    title: "",
    description: "",
    location_city: "",
    work_mode: "HYBRID",
    positions: 1,
    application_deadline: "",
    job_role_id: "",
    // internship
    duration_weeks: 12,
    stipend_min: 20000,
    stipend_max: 30000,
    // job
    salary_min: 800000,
    salary_max: 1500000,
    experience_min_years: 0,
    // live project
    expected_outcome: "",
    team_size_min: 2,
    team_size_max: 4,
  });
  const [skills, setSkills] = useState<DetectedSkill[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);

  const roles = useQuery({
    queryKey: ["job-roles", "posting"],
    queryFn: () => api.paged<JobRole>("/job-roles", { page_size: 60 }) as Promise<Paged<JobRole>>,
    staleTime: 10 * 60_000,
  });

  const analyse = useMutation({
    mutationFn: () =>
      api.post<AnalysisResult>("/opportunities/analyse-description", {
        description: form.description,
        title: form.title || undefined,
      }),
    onSuccess: (result) => {
      setAnalysis(result);
      setSkills(result.skills);
      if (result.suggested_job_role_id && !form.job_role_id) {
        setForm((current) => ({
          ...current,
          job_role_id: result.suggested_job_role_id ?? "",
        }));
      }
      toast.success(
        `Found ${result.skills.length} skill${result.skills.length === 1 ? "" : "s"} in the description`,
        { description: "Review and edit before publishing." },
      );
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not analyse"),
  });

  const create = useMutation({
    mutationFn: (publish: boolean) => {
      const base = {
        title: form.title,
        description: form.description,
        location_city: form.location_city || undefined,
        work_mode: form.work_mode,
        positions: Number(form.positions),
        application_deadline: form.application_deadline
          ? new Date(form.application_deadline).toISOString()
          : undefined,
        job_role_id: form.job_role_id || undefined,
        skills: skills.map((skill) => ({
          skill_id: skill.skill_id,
          required_level: skill.suggested_level,
          importance: skill.suggested_importance,
          weight: 1.0,
        })),
      };
      const payload =
        config.kind === "internship"
          ? {
              ...base,
              duration_weeks: Number(form.duration_weeks),
              stipend_min: Number(form.stipend_min),
              stipend_max: Number(form.stipend_max),
              is_paid: true,
            }
          : config.kind === "project"
            ? {
                ...base,
                problem_statement: form.description,
                expected_outcome: form.expected_outcome,
                team_size_min: Number(form.team_size_min),
                team_size_max: Number(form.team_size_max),
                timeline_weeks: Number(form.duration_weeks),
              }
            : {
                ...base,
                salary_min: Number(form.salary_min),
                salary_max: Number(form.salary_max),
                experience_min_years: Number(form.experience_min_years),
                employment_type: "FULL_TIME",
              };
      return api.post(`${config.endpoint}?publish=${publish}`, payload);
    },
    onSuccess: (_result, publish) => {
      toast.success(publish ? "Posting published" : "Draft saved");
      onCreated();
    },
    onError: (error) => {
      if (error instanceof ApiError) {
        const fields = error.fieldErrors;
        toast.error(error.message, {
          description: Object.values(fields).slice(0, 2).join(" · ") || undefined,
        });
      } else {
        toast.error("Could not create the posting");
      }
    },
  });

  const canSubmit = form.title.length > 2 && form.description.length > 20;

  return (
    <Dialog
      open
      onClose={onClose}
      title={`New ${config.kind}`}
      description="Describe the role, let the analyser extract the skills, then review before publishing."
      size="xl"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button
            variant="secondary"
            disabled={!canSubmit}
            isLoading={create.isPending && create.variables === false}
            onClick={() => create.mutate(false)}
          >
            Save as draft
          </Button>
          <Button
            disabled={!canSubmit || skills.length === 0}
            isLoading={create.isPending && create.variables === true}
            onClick={() => create.mutate(true)}
          >
            Publish
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Input
          label="Title"
          placeholder={
            config.kind === "internship"
              ? "Backend Engineering Intern"
              : "Backend Developer"
          }
          required
          value={form.title}
          onChange={(event) => setForm((c) => ({ ...c, title: event.target.value }))}
        />

        <div>
          <Textarea
            label="Description"
            placeholder="Describe the role, the work, and the skills it needs. Mention technologies by name — the analyser matches them against our taxonomy."
            rows={7}
            required
            value={form.description}
            onChange={(event) =>
              setForm((c) => ({ ...c, description: event.target.value }))
            }
            hint={`${form.description.length} characters — at least 20 needed`}
          />
          <Button
            className="mt-2"
            variant="subtle"
            size="sm"
            leftIcon={<Wand2 />}
            disabled={form.description.length < 30}
            isLoading={analyse.isPending}
            onClick={() => analyse.mutate()}
          >
            Extract skills from this description
          </Button>
        </div>

        {analysis && (
          <div className="rounded-xl border border-brand-200 bg-brand-50/50 p-4">
            <div className="flex items-center gap-2">
              <Sparkles className="size-4 text-brand-700" aria-hidden />
              <p className="text-sm font-medium text-brand-900">
                {skills.length} skill{skills.length === 1 ? "" : "s"} detected
              </p>
              <Badge tone="brand" className="ml-auto">
                {analysis.extracted_by === "deterministic"
                  ? "Exact taxonomy match"
                  : analysis.extracted_by}
              </Badge>
            </div>
            <p className="mt-1 text-xs text-brand-900/80">
              Only skills that literally appear in your text are listed. Edit the
              level and importance, or remove any that are not really required.
            </p>

            <ul className="mt-3 space-y-1.5">
              {skills.map((skill, index) => (
                <li
                  key={skill.skill_id}
                  className="flex flex-wrap items-center gap-2 rounded-lg bg-surface p-2"
                >
                  <span className="min-w-0 flex-1 truncate text-sm font-medium text-ink-900">
                    {skill.skill_name}
                    <span className="ml-1.5 text-2xs font-normal text-ink-400">
                      matched &ldquo;{skill.matched_term}&rdquo; ×{skill.occurrences}
                    </span>
                  </span>
                  <select
                    aria-label={`${skill.skill_name} level`}
                    value={skill.suggested_level}
                    onChange={(event) =>
                      setSkills((current) =>
                        current.map((entry, i) =>
                          i === index
                            ? { ...entry, suggested_level: event.target.value as ProficiencyLevel }
                            : entry,
                        ),
                      )
                    }
                    className="rounded-md border border-ink-200 py-1 pl-2 pr-6 text-2xs"
                  >
                    {["BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"].map((level) => (
                      <option key={level} value={level}>{level.toLowerCase()}</option>
                    ))}
                  </select>
                  <select
                    aria-label={`${skill.skill_name} importance`}
                    value={skill.suggested_importance}
                    onChange={(event) =>
                      setSkills((current) =>
                        current.map((entry, i) =>
                          i === index
                            ? {
                                ...entry,
                                suggested_importance: event.target.value as SkillImportance,
                              }
                            : entry,
                        ),
                      )
                    }
                    className="rounded-md border border-ink-200 py-1 pl-2 pr-6 text-2xs"
                  >
                    <option value="REQUIRED">required</option>
                    <option value="PREFERRED">preferred</option>
                    <option value="OPTIONAL">optional</option>
                  </select>
                  <button
                    type="button"
                    aria-label={`Remove ${skill.skill_name}`}
                    onClick={() =>
                      setSkills((current) => current.filter((_, i) => i !== index))
                    }
                    className="rounded p-1 text-ink-400 hover:bg-ink-100 hover:text-danger-600"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          <Select
            label="Canonical role"
            hint="Used to inherit a standard skill profile if you add none."
            value={form.job_role_id}
            onChange={(event) =>
              setForm((c) => ({ ...c, job_role_id: event.target.value }))
            }
          >
            <option value="">None</option>
            {roles.data?.data.map((role) => (
              <option key={role.id} value={role.id}>{role.title}</option>
            ))}
          </Select>
          <Input
            label="Location"
            placeholder="Bengaluru"
            value={form.location_city}
            onChange={(event) =>
              setForm((c) => ({ ...c, location_city: event.target.value }))
            }
          />
          <Select
            label="Work mode"
            value={form.work_mode}
            onChange={(event) => setForm((c) => ({ ...c, work_mode: event.target.value }))}
          >
            <option value="ONSITE">On-site</option>
            <option value="HYBRID">Hybrid</option>
            <option value="REMOTE">Remote</option>
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

          {config.kind === "project" ? (
            <>
              <Input
                label="Timeline (weeks)"
                type="number"
                min={1}
                max={104}
                value={form.duration_weeks}
                onChange={(event) =>
                  setForm((c) => ({ ...c, duration_weeks: Number(event.target.value) }))
                }
              />
              <div className="grid grid-cols-2 gap-2">
                <Input
                  label="Team size min"
                  type="number"
                  min={1}
                  value={form.team_size_min}
                  onChange={(event) =>
                    setForm((c) => ({ ...c, team_size_min: Number(event.target.value) }))
                  }
                />
                <Input
                  label="Team size max"
                  type="number"
                  min={1}
                  value={form.team_size_max}
                  onChange={(event) =>
                    setForm((c) => ({ ...c, team_size_max: Number(event.target.value) }))
                  }
                />
              </div>
              <div className="sm:col-span-2">
                <Textarea
                  label="Expected outcome"
                  rows={2}
                  placeholder="What a successful submission looks like."
                  value={form.expected_outcome}
                  onChange={(event) =>
                    setForm((c) => ({ ...c, expected_outcome: event.target.value }))
                  }
                />
              </div>
            </>
          ) : config.kind === "internship" ? (
            <>
              <Input
                label="Duration (weeks)"
                type="number"
                min={1}
                max={104}
                value={form.duration_weeks}
                onChange={(event) =>
                  setForm((c) => ({ ...c, duration_weeks: Number(event.target.value) }))
                }
              />
              <div className="grid grid-cols-2 gap-2">
                <Input
                  label="Stipend min"
                  type="number"
                  min={0}
                  value={form.stipend_min}
                  onChange={(event) =>
                    setForm((c) => ({ ...c, stipend_min: Number(event.target.value) }))
                  }
                />
                <Input
                  label="Stipend max"
                  type="number"
                  min={0}
                  value={form.stipend_max}
                  onChange={(event) =>
                    setForm((c) => ({ ...c, stipend_max: Number(event.target.value) }))
                  }
                />
              </div>
            </>
          ) : (
            <>
              <Input
                label="Minimum experience (years)"
                type="number"
                min={0}
                step={0.5}
                value={form.experience_min_years}
                onChange={(event) =>
                  setForm((c) => ({
                    ...c,
                    experience_min_years: Number(event.target.value),
                  }))
                }
              />
              <div className="grid grid-cols-2 gap-2">
                <Input
                  label="Salary min"
                  type="number"
                  min={0}
                  value={form.salary_min}
                  onChange={(event) =>
                    setForm((c) => ({ ...c, salary_min: Number(event.target.value) }))
                  }
                />
                <Input
                  label="Salary max"
                  type="number"
                  min={0}
                  value={form.salary_max}
                  onChange={(event) =>
                    setForm((c) => ({ ...c, salary_max: Number(event.target.value) }))
                  }
                />
              </div>
            </>
          )}

          <Input
            label="Application deadline"
            type="date"
            value={form.application_deadline}
            onChange={(event) =>
              setForm((c) => ({ ...c, application_deadline: event.target.value }))
            }
          />
        </div>

        {skills.length === 0 && (
          <p className="rounded-lg bg-warning-50 px-3 py-2 text-xs text-warning-600">
            A posting needs at least one skill before it can be published — that
            is what makes it findable by the matching engine.
          </p>
        )}
      </div>
    </Dialog>
  );
}
