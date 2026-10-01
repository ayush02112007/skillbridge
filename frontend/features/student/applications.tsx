"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Briefcase, Calendar, CheckCircle2, Circle, ExternalLink, XCircle,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Select, Textarea } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { APPLICATION_STATUS_LABELS, APPLICATION_STATUS_TONE } from "@/lib/constants";
import { cn, formatDate, formatDateTime, relativeTime } from "@/lib/utils";
import type {
  Application, ApplicationListItem, Paged, TimelineStep,
} from "@/types/api";

function Timeline({ steps }: { steps: TimelineStep[] }) {
  return (
    <ol className="flex flex-wrap items-center gap-x-1 gap-y-3">
      {steps.map((step, index) => {
        const done = step.state === "complete";
        const current = step.state === "current";
        const stopped = step.state === "stopped";
        const terminal = step.state === "terminal";
        const negative = terminal && ["REJECTED", "WITHDRAWN"].includes(step.status);

        return (
          <li key={step.status} className="flex items-center gap-1">
            <div className="flex flex-col items-center gap-1">
              <span
                className={cn(
                  "flex size-7 items-center justify-center rounded-full border-2 [&_svg]:size-3.5",
                  done && "border-success-500 bg-success-500 text-white",
                  current && "border-brand-600 bg-brand-600 text-white",
                  stopped && "border-ink-300 bg-ink-200 text-ink-500",
                  terminal &&
                    (negative
                      ? "border-danger-500 bg-danger-500 text-white"
                      : "border-success-500 bg-success-500 text-white"),
                  step.state === "upcoming" && "border-ink-200 bg-surface text-ink-300",
                )}
              >
                {done || (terminal && !negative) ? (
                  <CheckCircle2 />
                ) : negative ? (
                  <XCircle />
                ) : (
                  <Circle />
                )}
              </span>
              <span
                className={cn(
                  "max-w-[5.5rem] text-center text-2xs leading-tight",
                  current || terminal ? "font-medium text-ink-800" : "text-ink-500",
                )}
              >
                {step.label}
              </span>
            </div>
            {index < steps.length - 1 && (
              <span
                className={cn(
                  "mb-5 h-0.5 w-6 rounded-full",
                  done ? "bg-success-500" : "bg-ink-200",
                )}
                aria-hidden
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}

function ApplicationDetail({
  applicationId,
  onClose,
}: {
  applicationId: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");
  const [confirmWithdraw, setConfirmWithdraw] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["application", applicationId],
    queryFn: () => api.get<Application>(`/applications/${applicationId}`),
  });

  const withdraw = useMutation({
    mutationFn: () =>
      api.post(`/applications/${applicationId}/withdraw`, { reason }),
    onSuccess: () => {
      toast.success("Application withdrawn");
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
      void queryClient.invalidateQueries({ queryKey: ["application", applicationId] });
      setConfirmWithdraw(false);
      onClose();
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.message : "Could not withdraw"),
  });

  const canWithdraw =
    data && !["SELECTED", "REJECTED", "WITHDRAWN"].includes(data.status);

  return (
    <Dialog
      open
      onClose={onClose}
      title={data?.opportunity?.title ?? "Application"}
      description={data?.opportunity?.company?.name ?? undefined}
      size="lg"
      footer={
        <>
          {data?.opportunity && (
            <Link href={`/opportunities/${data.opportunity.id}`} className="mr-auto">
              <Button variant="ghost" size="sm" rightIcon={<ExternalLink />}>
                View posting
              </Button>
            </Link>
          )}
          {canWithdraw && (
            <Button
              variant="danger"
              size="sm"
              onClick={() => setConfirmWithdraw(true)}
            >
              Withdraw
            </Button>
          )}
          <Button variant="secondary" size="sm" onClick={onClose}>
            Close
          </Button>
        </>
      }
    >
      {isLoading && <SkeletonList count={2} rows={3} />}
      {error && <ErrorState error={error} />}

      {data && (
        <div className="space-y-6">
          <div className="overflow-x-auto pb-1">
            <Timeline steps={data.timeline} />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-ink-200 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
                Match at time of applying
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-ink-900">
                {Math.round(data.match_score)}%
              </p>
              <div className="mt-2.5 space-y-1">
                {Object.entries(data.match_breakdown).slice(0, 4).map(([factor, value]) => (
                  <div key={factor} className="flex items-center gap-2">
                    <span className="w-24 shrink-0 truncate text-2xs capitalize text-ink-500">
                      {factor}
                    </span>
                    <Progress value={Number(value) * 100} size="sm" className="flex-1" />
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-ink-200 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
                Skills
              </p>
              <div className="mt-2 flex flex-wrap gap-1">
                {data.matching_skills.slice(0, 6).map((skill) => (
                  <Badge key={skill} tone="success">{skill}</Badge>
                ))}
              </div>
              {data.missing_skills.length > 0 && (
                <>
                  <p className="mt-3 text-2xs text-ink-500">Gaps at the time:</p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {data.missing_skills.slice(0, 5).map((skill) => (
                      <Badge key={skill} tone="warning">{skill}</Badge>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>

          {data.interviews.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-ink-900">Interviews</h3>
              <ul className="space-y-2">
                {data.interviews.map((interview) => (
                  <li
                    key={interview.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-ink-200 p-3"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink-900">
                        Round {interview.round_number}: {interview.round_name}
                      </p>
                      <p className="text-xs text-ink-500">
                        {formatDateTime(interview.scheduled_at)} · {interview.duration_minutes} min ·{" "}
                        {interview.mode.toLowerCase()}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge tone={interview.status === "SCHEDULED" ? "brand" : "neutral"}>
                        {interview.status.toLowerCase()}
                      </Badge>
                      {interview.location_or_link?.startsWith("http") && (
                        <a href={interview.location_or_link} target="_blank" rel="noreferrer">
                          <Button size="sm" variant="secondary" rightIcon={<ExternalLink />}>
                            Join
                          </Button>
                        </a>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <h3 className="mb-2 text-sm font-semibold text-ink-900">History</h3>
            <ol className="space-y-2 border-l border-ink-200 pl-4">
              {data.history.map((entry, index) => (
                <li key={index} className="relative">
                  <span
                    className="absolute -left-[21px] top-1.5 size-2 rounded-full bg-ink-300"
                    aria-hidden
                  />
                  <p className="text-sm text-ink-800">
                    {APPLICATION_STATUS_LABELS[entry.to_status]}
                    {entry.note && <span className="text-ink-500"> — {entry.note}</span>}
                  </p>
                  <p className="text-2xs text-ink-400">{formatDateTime(entry.created_at)}</p>
                </li>
              ))}
            </ol>
          </div>

          {data.rejection_reason && (
            <div className="rounded-xl border border-ink-200 bg-surface-muted p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
                Feedback from the employer
              </p>
              <p className="mt-1 text-sm text-ink-700">{data.rejection_reason}</p>
            </div>
          )}
        </div>
      )}

      {confirmWithdraw && (
        <Dialog
          open
          onClose={() => setConfirmWithdraw(false)}
          title="Withdraw this application?"
          description="This is final. You will not be able to apply to this posting again."
          size="sm"
          footer={
            <>
              <Button variant="secondary" size="sm" onClick={() => setConfirmWithdraw(false)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                isLoading={withdraw.isPending}
                onClick={() => withdraw.mutate()}
              >
                Withdraw application
              </Button>
            </>
          }
        >
          <Textarea
            label="Reason (optional)"
            placeholder="e.g. Accepted another offer"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </Dialog>
      )}
    </Dialog>
  );
}

export function StudentApplications() {
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["applications", "mine", status],
    queryFn: () =>
      api.paged<ApplicationListItem>("/applications/mine", {
        status: status || undefined,
        page_size: 40,
      }) as Promise<Paged<ApplicationListItem>>,
  });

  const funnel = useQuery({
    queryKey: ["applications", "funnel"],
    queryFn: () =>
      api.get<{
        total: number;
        by_status: Record<string, number>;
        conversion: Record<string, number>;
      }>("/applications/mine/funnel"),
  });

  return (
    <>
      <PageHeader
        title="My applications"
        description="Every application, and exactly where it stands."
      >
        {funnel.data && funnel.data.total > 0 && (
          <div className="grid gap-3 sm:grid-cols-4">
            {[
              ["Applied", funnel.data.total],
              ["Shortlisted", funnel.data.by_status.SHORTLISTED ?? 0],
              ["Interviewing", funnel.data.by_status.INTERVIEW ?? 0],
              ["Offers", (funnel.data.by_status.OFFERED ?? 0) + (funnel.data.by_status.SELECTED ?? 0)],
            ].map(([label, value]) => (
              <Card key={label as string} className="p-4">
                <p className="text-xs text-ink-500">{label}</p>
                <p className="mt-0.5 text-xl font-semibold tabular-nums text-ink-900">
                  {value as number}
                </p>
              </Card>
            ))}
          </div>
        )}
      </PageHeader>

      <div className="mb-4 max-w-xs">
        <Select
          label="Filter by status"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        >
          <option value="">All applications</option>
          {Object.entries(APPLICATION_STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </Select>
      </div>

      {isLoading && <SkeletonList count={4} rows={2} />}
      {error && <ErrorState error={error} onRetry={() => void refetch()} />}

      {data && data.data.length === 0 && (
        <EmptyState
          icon={<Briefcase />}
          title={status ? "No applications with that status" : "No applications yet"}
          description={
            status
              ? "Try clearing the filter to see everything."
              : "When you apply to an internship or job, you'll track it here from application through to offer."
          }
          action={
            <Link href="/student/internships">
              <Button size="sm">Find internships</Button>
            </Link>
          }
        />
      )}

      {data && data.data.length > 0 && (
        <div className="space-y-3">
          {data.data.map((application) => (
            <Card key={application.id} className="p-5" interactive>
              <button
                type="button"
                onClick={() => setSelected(application.id)}
                className="w-full text-left"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-[15px] font-semibold text-ink-900">
                      {application.opportunity?.title}
                    </p>
                    <p className="truncate text-sm text-ink-500">
                      {application.opportunity?.company?.name} · applied{" "}
                      {relativeTime(application.submitted_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs tabular-nums text-ink-500">
                      {Math.round(application.match_score)}% match
                    </span>
                    <Badge tone={APPLICATION_STATUS_TONE[application.status]} size="md">
                      {APPLICATION_STATUS_LABELS[application.status]}
                    </Badge>
                  </div>
                </div>

                {application.next_interview_at && (
                  <p className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-warning-50 px-2.5 py-1 text-xs font-medium text-warning-600">
                    <Calendar className="size-3.5" aria-hidden />
                    Interview {formatDateTime(application.next_interview_at)}
                  </p>
                )}

                {application.matching_skills.length > 0 && (
                  <div className="mt-2.5 flex flex-wrap gap-1">
                    {application.matching_skills.slice(0, 4).map((skill) => (
                      <Badge key={skill} tone="success">{skill}</Badge>
                    ))}
                  </div>
                )}
              </button>
            </Card>
          ))}
        </div>
      )}

      {selected && (
        <ApplicationDetail applicationId={selected} onClose={() => setSelected(null)} />
      )}
    </>
  );
}
