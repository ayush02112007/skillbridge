"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Calendar, ExternalLink, Filter, Info, Star, UserCheck,
} from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input, Select, Textarea } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { Tooltip } from "@/components/ui/tooltip";
import { api, ApiError } from "@/lib/api";
import {
  APPLICATION_STATUS_LABELS, APPLICATION_STATUS_TONE, MATCH_FACTOR_LABELS,
  NEXT_STATUSES,
} from "@/lib/constants";
import { formatDateTime, relativeTime } from "@/lib/utils";
import type {
  Application, ApplicationListItem, ApplicationStatus, Opportunity, Paged,
} from "@/types/api";

function ApplicantDetail({
  applicationId,
  onClose,
}: {
  applicationId: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const [interviewOpen, setInterviewOpen] = useState(false);
  const [interview, setInterview] = useState({
    scheduled_at: "",
    round_name: "Technical Round",
    duration_minutes: 45,
    mode: "ONLINE",
    location_or_link: "",
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["application", applicationId],
    queryFn: () => api.get<Application>(`/applications/${applicationId}`),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["application", applicationId] });
    void queryClient.invalidateQueries({ queryKey: ["applicants"] });
    void queryClient.invalidateQueries({ queryKey: ["industry"] });
  };

  const changeStatus = useMutation({
    mutationFn: (status: ApplicationStatus) =>
      api.patch<Application>(`/applications/${applicationId}`, { status, note }),
    onSuccess: (updated) => {
      toast.success(`Moved to ${APPLICATION_STATUS_LABELS[updated.status]}`);
      setNote("");
      invalidate();
    },
    onError: (err) => {
      const message = err instanceof ApiError ? err.message : "Could not update";
      const allowed =
        err instanceof ApiError
          ? (err.details as { allowed_next?: string[] } | undefined)?.allowed_next
          : undefined;
      toast.error(message, {
        description: allowed?.length ? `Allowed next: ${allowed.join(", ")}` : undefined,
      });
    },
  });

  const saveNotes = useMutation({
    mutationFn: (payload: { recruiter_notes?: string; recruiter_rating?: number }) =>
      api.patch<Application>(`/applications/${applicationId}/notes`, payload),
    onSuccess: () => {
      toast.success("Saved");
      invalidate();
    },
  });

  const scheduleInterview = useMutation({
    mutationFn: () =>
      api.post(`/applications/${applicationId}/interviews`, {
        ...interview,
        scheduled_at: new Date(interview.scheduled_at).toISOString(),
      }),
    onSuccess: () => {
      toast.success("Interview scheduled and the candidate notified");
      setInterviewOpen(false);
      invalidate();
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.message : "Could not schedule"),
  });

  const applicant = data?.applicant;
  const nextStatuses = data ? NEXT_STATUSES[data.status] : [];

  return (
    <Dialog
      open
      onClose={onClose}
      title={applicant?.full_name ?? "Applicant"}
      description={data?.opportunity?.title}
      size="xl"
      footer={
        <>
          {applicant?.portfolio_slug && (
            <Link
              href={`/portfolio/${applicant.portfolio_slug}`}
              target="_blank"
              className="mr-auto"
            >
              <Button variant="ghost" size="sm" rightIcon={<ExternalLink />}>
                View portfolio
              </Button>
            </Link>
          )}
          <Button variant="secondary" size="sm" onClick={onClose}>Close</Button>
        </>
      }
    >
      {isLoading && <SkeletonList count={2} rows={3} />}
      {error && <ErrorState error={error} />}

      {data && applicant && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-start gap-4">
            <Avatar name={applicant.full_name} src={applicant.avatar_url} size="lg" />
            <div className="min-w-0 flex-1">
              <p className="text-lg font-semibold text-ink-900">{applicant.full_name}</p>
              {applicant.headline && (
                <p className="text-sm text-ink-600">{applicant.headline}</p>
              )}
              <p className="mt-1 text-xs text-ink-500">
                {applicant.institution_name}
                {applicant.graduation_year ? ` · Class of ${applicant.graduation_year}` : ""}
                {applicant.cgpa ? ` · CGPA ${applicant.cgpa}` : ""}
                {applicant.city ? ` · ${applicant.city}` : ""}
              </p>
            </div>
            <div className="text-right">
              <p className="text-3xl font-semibold tabular-nums text-brand-700">
                {Math.round(data.match_score)}%
              </p>
              <p className="text-2xs text-ink-500">skill match</p>
            </div>
          </div>

          <div className="flex gap-2 rounded-lg bg-surface-muted p-3">
            <Info className="mt-0.5 size-4 shrink-0 text-ink-400" aria-hidden />
            <p className="text-xs leading-relaxed text-ink-600">
              The match score is decision support. It reflects evidenced skills,
              education fit and stated preferences only — never protected
              characteristics — and the hiring decision remains yours.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-ink-200 p-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
                Match breakdown
              </p>
              <div className="space-y-1.5">
                {Object.entries(data.match_breakdown).map(([factor, value]) => (
                  <div key={factor} className="flex items-center gap-2">
                    <span className="w-32 shrink-0 truncate text-2xs text-ink-500">
                      {MATCH_FACTOR_LABELS[factor] ?? factor}
                    </span>
                    <Progress value={Number(value) * 100} size="sm" className="flex-1" />
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-ink-200 p-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
                Skills
              </p>
              <div className="flex flex-wrap gap-1">
                {data.matching_skills.map((skill) => (
                  <Badge key={skill} tone="success">{skill}</Badge>
                ))}
              </div>
              {data.missing_skills.length > 0 && (
                <>
                  <p className="mt-2.5 text-2xs text-ink-500">Missing:</p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {data.missing_skills.slice(0, 6).map((skill) => (
                      <Badge key={skill} tone="warning">{skill}</Badge>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>

          {data.cover_letter && (
            <div>
              <h3 className="mb-1.5 text-sm font-semibold text-ink-900">Cover note</h3>
              <p className="whitespace-pre-line rounded-xl bg-surface-muted p-4 text-sm leading-relaxed text-ink-700">
                {data.cover_letter}
              </p>
            </div>
          )}

          {data.interviews.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-ink-900">Interviews</h3>
              <ul className="space-y-2">
                {data.interviews.map((round) => (
                  <li
                    key={round.id}
                    className="flex items-center justify-between gap-2 rounded-xl border border-ink-200 p-3 text-sm"
                  >
                    <span>
                      Round {round.round_number}: {round.round_name}
                      <span className="ml-2 text-xs text-ink-500">
                        {formatDateTime(round.scheduled_at)}
                      </span>
                    </span>
                    <Badge tone={round.status === "SCHEDULED" ? "brand" : "neutral"}>
                      {round.status.toLowerCase()}
                    </Badge>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Decision panel */}
          <div className="rounded-xl border border-ink-200 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold text-ink-900">
                Current stage:{" "}
                <Badge tone={APPLICATION_STATUS_TONE[data.status]} size="md">
                  {APPLICATION_STATUS_LABELS[data.status]}
                </Badge>
              </p>
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((rating) => (
                  <button
                    key={rating}
                    type="button"
                    aria-label={`Rate ${rating} of 5`}
                    onClick={() => saveNotes.mutate({ recruiter_rating: rating })}
                    className="p-0.5"
                  >
                    <Star
                      className={
                        (data.recruiter_rating ?? 0) >= rating
                          ? "size-4 fill-accent-400 text-accent-400"
                          : "size-4 text-ink-300"
                      }
                    />
                  </button>
                ))}
              </div>
            </div>

            <Textarea
              className="mt-3"
              label="Internal note (never shown to the candidate)"
              placeholder="Context for your team…"
              rows={2}
              defaultValue={data.recruiter_notes ?? ""}
              onBlur={(event) =>
                event.target.value !== (data.recruiter_notes ?? "") &&
                saveNotes.mutate({ recruiter_notes: event.target.value })
              }
            />

            {nextStatuses.length > 0 ? (
              <>
                <Textarea
                  className="mt-3"
                  label="Note for this decision (shared in the timeline)"
                  placeholder="Optional"
                  rows={2}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                />
                <div className="mt-3 flex flex-wrap gap-2">
                  {nextStatuses.map((status) => (
                    <Button
                      key={status}
                      size="sm"
                      variant={status === "REJECTED" ? "danger" : "primary"}
                      isLoading={changeStatus.isPending && changeStatus.variables === status}
                      onClick={() => changeStatus.mutate(status)}
                    >
                      {APPLICATION_STATUS_LABELS[status]}
                    </Button>
                  ))}
                  {["SHORTLISTED", "INTERVIEW"].includes(data.status) && (
                    <Button
                      size="sm"
                      variant="secondary"
                      leftIcon={<Calendar />}
                      onClick={() => setInterviewOpen(true)}
                    >
                      Schedule interview
                    </Button>
                  )}
                </div>
              </>
            ) : (
              <p className="mt-3 text-sm text-ink-500">
                This application has reached a final state and cannot be moved further.
              </p>
            )}
          </div>
        </div>
      )}

      {interviewOpen && (
        <Dialog
          open
          onClose={() => setInterviewOpen(false)}
          title="Schedule an interview"
          description="The candidate is notified by email and in-app immediately."
          footer={
            <>
              <Button variant="secondary" size="sm" onClick={() => setInterviewOpen(false)}>
                Cancel
              </Button>
              <Button
                size="sm"
                isLoading={scheduleInterview.isPending}
                disabled={!interview.scheduled_at}
                onClick={() => scheduleInterview.mutate()}
              >
                Schedule
              </Button>
            </>
          }
        >
          <div className="space-y-3">
            <Input
              label="Date and time"
              type="datetime-local"
              required
              value={interview.scheduled_at}
              onChange={(event) =>
                setInterview((current) => ({ ...current, scheduled_at: event.target.value }))
              }
            />
            <Input
              label="Round name"
              value={interview.round_name}
              onChange={(event) =>
                setInterview((current) => ({ ...current, round_name: event.target.value }))
              }
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <Select
                label="Mode"
                value={interview.mode}
                onChange={(event) =>
                  setInterview((current) => ({ ...current, mode: event.target.value }))
                }
              >
                <option value="ONLINE">Online</option>
                <option value="ONSITE">On-site</option>
                <option value="PHONE">Phone</option>
              </Select>
              <Input
                label="Duration (minutes)"
                type="number"
                min={10}
                max={480}
                value={interview.duration_minutes}
                onChange={(event) =>
                  setInterview((current) => ({
                    ...current,
                    duration_minutes: Number(event.target.value),
                  }))
                }
              />
            </div>
            <Input
              label="Meeting link or location"
              placeholder="https://meet.example.com/…"
              value={interview.location_or_link}
              onChange={(event) =>
                setInterview((current) => ({
                  ...current,
                  location_or_link: event.target.value,
                }))
              }
            />
          </div>
        </Dialog>
      )}
    </Dialog>
  );
}

export function IndustryApplicants() {
  const params = useSearchParams();
  const [selected, setSelected] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [opportunityId, setOpportunityId] = useState("");
  const [minMatch, setMinMatch] = useState("");
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("match");

  useEffect(() => {
    const fromUrl = params.get("application");
    if (fromUrl) setSelected(fromUrl);
    const opportunity = params.get("opportunity");
    if (opportunity) setOpportunityId(opportunity);
  }, [params]);

  const postings = useQuery({
    queryKey: ["industry", "postings", "all"],
    queryFn: async () => {
      const [jobs, internships] = await Promise.all([
        api.paged<Opportunity>("/jobs/mine", { page_size: 50 }),
        api.paged<Opportunity>("/internships/mine", { page_size: 50 }),
      ]);
      return [...jobs.data, ...internships.data];
    },
  });

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["applicants", { status, opportunityId, minMatch, search, sortBy }],
    queryFn: () =>
      api.paged<ApplicationListItem>("/applications/received", {
        status: status || undefined,
        opportunity_id: opportunityId || undefined,
        min_match_score: minMatch || undefined,
        q: search || undefined,
        sort_by: sortBy,
        page_size: 40,
      }) as Promise<Paged<ApplicationListItem>>,
  });

  return (
    <>
      <PageHeader
        title="Applicants"
        description="Ranked by evidenced skill fit. Every score shows its working, and nobody is filtered out automatically."
      />

      <Card className="mb-5 p-4">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setSearch(query);
          }}
          className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"
        >
          <Input
            label="Search name"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <Select
            label="Posting"
            value={opportunityId}
            onChange={(event) => setOpportunityId(event.target.value)}
          >
            <option value="">All postings</option>
            {postings.data?.map((posting) => (
              <option key={posting.id} value={posting.id}>{posting.title}</option>
            ))}
          </Select>
          <Select
            label="Status"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">Any stage</option>
            {Object.entries(APPLICATION_STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </Select>
          <Select
            label="Minimum match"
            value={minMatch}
            onChange={(event) => setMinMatch(event.target.value)}
          >
            <option value="">Any</option>
            <option value="40">40%+</option>
            <option value="60">60%+</option>
            <option value="70">70%+</option>
            <option value="80">80%+</option>
          </Select>
          <div className="flex items-end gap-2">
            <Select
              label="Sort"
              value={sortBy}
              onChange={(event) => setSortBy(event.target.value)}
              className="flex-1"
            >
              <option value="match">Best match</option>
              <option value="recent">Most recent</option>
            </Select>
            <Button type="submit">Apply</Button>
          </div>
        </form>
      </Card>

      {isLoading && <SkeletonList count={5} rows={2} />}
      {error && <ErrorState error={error} onRetry={() => void refetch()} />}

      {data && data.data.length === 0 && (
        <EmptyState
          icon={<UserCheck />}
          title="No applicants match these filters"
          description="Try widening the match threshold or clearing the posting filter."
        />
      )}

      {data && data.data.length > 0 && (
        <>
          <p className="mb-3 text-sm text-ink-500">
            {data.meta.total} applicant{data.meta.total === 1 ? "" : "s"}
          </p>
          <div className="space-y-3">
            {data.data.map((application) => (
              <Card key={application.id} interactive className="p-4">
                <button
                  type="button"
                  onClick={() => setSelected(application.id)}
                  className="flex w-full items-center gap-4 text-left"
                >
                  <Avatar
                    name={application.applicant?.full_name}
                    src={application.applicant?.avatar_url}
                    size="md"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-ink-900">
                      {application.applicant?.full_name}
                    </p>
                    <p className="truncate text-xs text-ink-500">
                      {application.opportunity?.title} ·{" "}
                      {application.applicant?.institution_name ?? "—"}
                      {application.applicant?.graduation_year
                        ? ` · ${application.applicant.graduation_year}`
                        : ""}
                    </p>
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {application.matching_skills.slice(0, 4).map((skill) => (
                        <Badge key={skill} tone="success">{skill}</Badge>
                      ))}
                      {application.missing_skills.slice(0, 2).map((skill) => (
                        <Badge key={skill} tone="warning">{skill}</Badge>
                      ))}
                    </div>
                  </div>

                  <div className="hidden w-28 shrink-0 sm:block">
                    <Tooltip content="Skill compatibility — decision support only">
                      <div className="w-full">
                        <Progress value={application.match_score} size="sm" showValue />
                      </div>
                    </Tooltip>
                  </div>

                  <div className="shrink-0 text-right">
                    <Badge tone={APPLICATION_STATUS_TONE[application.status]} size="md">
                      {APPLICATION_STATUS_LABELS[application.status]}
                    </Badge>
                    <p className="mt-1 text-2xs text-ink-400">
                      {relativeTime(application.submitted_at)}
                    </p>
                  </div>
                </button>
              </Card>
            ))}
          </div>
        </>
      )}

      {selected && (
        <ApplicantDetail applicationId={selected} onClose={() => setSelected(null)} />
      )}
    </>
  );
}
