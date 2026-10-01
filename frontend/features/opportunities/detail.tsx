"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle, ArrowLeft, Bookmark, BookmarkCheck, Briefcase, Building2,
  Calendar, CheckCircle2, Clock, Compass, GraduationCap, Info, MapPin, Users,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Select, Textarea } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { ErrorState, SkeletonCard } from "@/components/ui/states";
import { Tooltip } from "@/components/ui/tooltip";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { APP_NAME, MATCH_FACTOR_LABELS, WORK_MODE_LABELS } from "@/lib/constants";
import { cn, daysUntil, formatDate, formatRange } from "@/lib/utils";
import type { Application, OpportunityDetail } from "@/types/api";

function MatchPanel({ detail }: { detail: OpportunityDetail }) {
  const match = detail.match;
  if (!match) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Why this is a {Math.round(match.match_score)}% match</CardTitle>
        <p className="text-sm text-ink-500">
          A recommendation score, not a prediction of selection.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm leading-relaxed text-ink-700">{match.reason_summary}</p>

        <div className="space-y-2">
          {Object.entries(match.breakdown).map(([factor, value]) => (
            <div key={factor} className="flex items-center gap-3">
              <span className="w-36 shrink-0 text-xs text-ink-600">
                {MATCH_FACTOR_LABELS[factor] ?? factor}
              </span>
              <Progress value={Number(value) * 100} size="sm" className="flex-1" />
              <span className="w-11 shrink-0 text-right text-xs tabular-nums text-ink-500">
                +{(match.contributions[factor] ?? 0).toFixed(1)}
              </span>
            </div>
          ))}
        </div>

        {match.reasons.length > 0 && (
          <ul className="space-y-1.5 border-t border-ink-100 pt-3">
            {match.reasons.map((reason) => (
              <li key={reason} className="flex gap-2 text-xs leading-relaxed text-ink-600">
                <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-success-500" aria-hidden />
                {reason}
              </li>
            ))}
          </ul>
        )}

        {match.next_steps.length > 0 && (
          <div className="rounded-xl bg-surface-muted p-3.5">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
              To strengthen this application
            </p>
            <ul className="mt-1.5 space-y-1">
              {match.next_steps.map((step) => (
                <li key={step} className="text-xs text-ink-700">
                  • {step}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function OpportunityDetailView({ opportunityId }: { opportunityId: string }) {
  const { isAuthenticated, hasRole, session } = useAuth();
  const queryClient = useQueryClient();
  const router = useRouter();
  const [applyOpen, setApplyOpen] = useState(false);
  const [coverLetter, setCoverLetter] = useState("");

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["opportunity", opportunityId],
    queryFn: () => api.get<OpportunityDetail>(`/opportunities/${opportunityId}`),
  });

  const apply = useMutation({
    mutationFn: () =>
      api.post<Application>(`/applications/opportunities/${opportunityId}`, {
        cover_letter: coverLetter,
      }),
    onSuccess: () => {
      toast.success("Application submitted");
      setApplyOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["opportunity", opportunityId] });
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
      router.push("/student/applications");
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        const details = err.details as { reasons?: string[] } | undefined;
        toast.error(err.message, {
          description: details?.reasons?.join(" · "),
        });
      } else {
        toast.error("Could not submit your application");
      }
    },
  });

  const toggleSave = useMutation({
    mutationFn: async () => {
      if (data?.is_saved) {
        await api.delete(`/opportunities/${opportunityId}/save`);
        return false;
      }
      await api.post(`/opportunities/${opportunityId}/save`);
      return true;
    },
    onSuccess: (saved) => {
      toast.success(saved ? "Saved" : "Removed from saved");
      void queryClient.invalidateQueries({ queryKey: ["opportunity", opportunityId] });
    },
  });

  const isStudent = hasRole("STUDENT");

  if (isLoading) {
    return (
      <div className="container py-8">
        <SkeletonCard rows={6} />
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="container py-8">
        <ErrorState error={error} onRetry={() => void refetch()} />
      </div>
    );
  }

  const isInternship = data.opportunity_type === "INTERNSHIP";
  const compensation = isInternship
    ? formatRange(
        data.details.stipend_min as number,
        data.details.stipend_max as number,
      )
    : formatRange(data.details.salary_min as number, data.details.salary_max as number);
  const deadline = daysUntil(data.application_deadline);
  const ineligible = data.match?.is_eligible === false;

  return (
    <div className="min-h-dvh bg-surface-muted">
      {!isAuthenticated && (
        <header className="border-b border-ink-200 bg-surface">
          <div className="container flex h-16 items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="flex size-8 items-center justify-center rounded-lg bg-brand-700 text-white">
                <Compass className="size-4" aria-hidden />
              </span>
              <span className="text-[17px] font-semibold text-ink-950">{APP_NAME}</span>
            </Link>
            <Link href="/register">
              <Button size="sm">Get started</Button>
            </Link>
          </div>
        </header>
      )}

      <main id="main" className="container py-6 lg:py-8">
        <Link
          href={isAuthenticated && session ? session.home_route : "/opportunities"}
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-ink-500 hover:text-ink-800"
        >
          <ArrowLeft className="size-4" aria-hidden />
          Back
        </Link>

        <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
          <div className="space-y-6">
            <Card className="p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex flex-wrap gap-1.5">
                    <Badge tone="brand" size="md">
                      {data.opportunity_type === "LIVE_PROJECT"
                        ? "Live project"
                        : isInternship
                          ? "Internship"
                          : "Job"}
                    </Badge>
                    {data.company?.verification_status === "VERIFIED" && (
                      <Badge tone="success">Verified company</Badge>
                    )}
                    {data.is_demo && <Badge tone="neutral">Demo data</Badge>}
                  </div>
                  <h1 className="mt-3 text-2xl">{data.title}</h1>
                  <p className="mt-1 flex items-center gap-1.5 text-sm text-ink-600">
                    <Building2 className="size-4 text-ink-400" aria-hidden />
                    {data.company?.name}
                    {data.company?.industry_sector ? ` · ${data.company.industry_sector}` : ""}
                  </p>
                </div>

                {data.match_score !== null && data.match_score !== undefined && (
                  <Tooltip content="How well your evidenced skills fit this posting.">
                    <div className="text-right">
                      <p className="text-3xl font-semibold tabular-nums text-brand-700">
                        {Math.round(data.match_score)}%
                      </p>
                      <p className="text-2xs text-ink-500">match</p>
                    </div>
                  </Tooltip>
                )}
              </div>

              <dl className="mt-5 grid gap-4 border-t border-ink-100 pt-5 sm:grid-cols-4">
                <div>
                  <dt className="text-2xs uppercase tracking-wide text-ink-500">Location</dt>
                  <dd className="mt-0.5 flex items-center gap-1 text-sm text-ink-800">
                    <MapPin className="size-3.5 text-ink-400" aria-hidden />
                    {data.location_city ?? "—"}
                  </dd>
                  <dd className="text-2xs text-ink-500">{WORK_MODE_LABELS[data.work_mode]}</dd>
                </div>
                <div>
                  <dt className="text-2xs uppercase tracking-wide text-ink-500">
                    {isInternship ? "Stipend" : "Salary"}
                  </dt>
                  <dd className="mt-0.5 text-sm font-medium text-ink-800">{compensation}</dd>
                  {isInternship && data.details.duration_weeks ? (
                    <dd className="text-2xs text-ink-500">
                      {String(data.details.duration_weeks)} weeks
                    </dd>
                  ) : null}
                </div>
                <div>
                  <dt className="text-2xs uppercase tracking-wide text-ink-500">Positions</dt>
                  <dd className="mt-0.5 flex items-center gap-1 text-sm text-ink-800">
                    <Users className="size-3.5 text-ink-400" aria-hidden />
                    {data.positions}
                  </dd>
                  <dd className="text-2xs text-ink-500">
                    {data.applications_count} applied
                  </dd>
                </div>
                <div>
                  <dt className="text-2xs uppercase tracking-wide text-ink-500">Deadline</dt>
                  <dd className="mt-0.5 flex items-center gap-1 text-sm text-ink-800">
                    <Calendar className="size-3.5 text-ink-400" aria-hidden />
                    {formatDate(data.application_deadline)}
                  </dd>
                  {deadline !== null && (
                    <dd
                      className={cn(
                        "text-2xs",
                        deadline <= 3 ? "font-medium text-danger-600" : "text-ink-500",
                      )}
                    >
                      {deadline <= 0 ? "Closed" : `${deadline} days left`}
                    </dd>
                  )}
                </div>
              </dl>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>About this role</CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                <p className="whitespace-pre-line text-sm leading-relaxed text-ink-700">
                  {data.description}
                </p>

                {data.responsibilities.length > 0 && (
                  <div>
                    <h3 className="mb-2 text-sm font-semibold text-ink-900">
                      What you&rsquo;ll do
                    </h3>
                    <ul className="space-y-1.5">
                      {data.responsibilities.map((item, index) => (
                        <li
                          key={index}
                          className="flex gap-2 text-sm leading-relaxed text-ink-700"
                        >
                          <span className="mt-1.5 size-1 shrink-0 rounded-full bg-ink-300" aria-hidden />
                          {String(item)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {isInternship && Array.isArray(data.details.learning_outcomes) &&
                  (data.details.learning_outcomes as string[]).length > 0 && (
                    <div>
                      <h3 className="mb-2 text-sm font-semibold text-ink-900">
                        What you&rsquo;ll learn
                      </h3>
                      <ul className="space-y-1.5">
                        {(data.details.learning_outcomes as string[]).map((item) => (
                          <li key={item} className="flex gap-2 text-sm text-ink-700">
                            <GraduationCap className="mt-0.5 size-4 shrink-0 text-brand-600" aria-hidden />
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                {data.perks.length > 0 && (
                  <div>
                    <h3 className="mb-2 text-sm font-semibold text-ink-900">Perks</h3>
                    <div className="flex flex-wrap gap-1.5">
                      {data.perks.map((perk, index) => (
                        <Badge key={index} tone="neutral" size="md">{String(perk)}</Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Skills this role requires</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="divide-y divide-ink-100">
                  {data.skills.map((skill) => {
                    const held = data.matching_skills?.includes(skill.skill?.name ?? "");
                    const missing = data.missing_skills?.includes(skill.skill?.name ?? "");
                    return (
                      <li key={skill.skill_id} className="flex items-center gap-3 py-2.5">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-ink-900">
                            {skill.skill?.name}
                          </p>
                          <p className="text-xs text-ink-500">
                            {skill.required_level.toLowerCase()} ·{" "}
                            {skill.importance.toLowerCase()}
                          </p>
                        </div>
                        {held && <Badge tone="success">You meet this</Badge>}
                        {missing && <Badge tone="warning">Gap</Badge>}
                      </li>
                    );
                  })}
                </ul>
              </CardContent>
            </Card>

            {(data.eligibility_text ||
              data.min_cgpa ||
              data.eligible_graduation_years.length > 0) && (
              <Card>
                <CardHeader>
                  <CardTitle>Eligibility</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm text-ink-700">
                  {data.eligibility_text && <p>{data.eligibility_text}</p>}
                  <ul className="space-y-1">
                    {data.min_cgpa ? <li>• Minimum CGPA {data.min_cgpa}</li> : null}
                    {data.max_backlogs !== null && data.max_backlogs !== undefined ? (
                      <li>• At most {data.max_backlogs} active backlog(s)</li>
                    ) : null}
                    {data.eligible_graduation_years.length > 0 && (
                      <li>
                        • Graduating in {data.eligible_graduation_years.join(", ")}
                      </li>
                    )}
                    {data.eligible_degrees.length > 0 && (
                      <li>
                        • Degrees:{" "}
                        {data.eligible_degrees
                          .map((degree) => String(degree).toLowerCase())
                          .join(", ")}
                      </li>
                    )}
                  </ul>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sticky action rail */}
          <div className="space-y-6 lg:sticky lg:top-24 lg:self-start">
            <Card className="p-5">
              {!isAuthenticated ? (
                <div className="space-y-3 text-center">
                  <p className="text-sm text-ink-600">
                    Sign in to see your match score and apply.
                  </p>
                  <Link href={`/login?next=/opportunities/${opportunityId}`}>
                    <Button block>Sign in</Button>
                  </Link>
                  <Link href="/register">
                    <Button block variant="secondary">Create an account</Button>
                  </Link>
                </div>
              ) : !isStudent ? (
                <p className="text-center text-sm text-ink-600">
                  Applications are open to student accounts.
                </p>
              ) : data.has_applied ? (
                <div className="space-y-3 text-center">
                  <Badge tone="success" size="md">
                    <CheckCircle2 className="size-3.5" aria-hidden />
                    Application submitted
                  </Badge>
                  <Link href="/student/applications">
                    <Button block variant="secondary">Track your application</Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  {ineligible && (
                    <div className="flex gap-2 rounded-lg border border-warning-500/25 bg-warning-50 p-3">
                      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning-600" aria-hidden />
                      <div className="text-xs leading-relaxed text-warning-600">
                        <p className="font-medium">You don&rsquo;t meet the stated criteria</p>
                        <ul className="mt-1 space-y-0.5">
                          {data.match?.ineligibility_reasons.map((reason) => (
                            <li key={reason}>• {reason}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                  <Button
                    block
                    size="lg"
                    disabled={!data.is_open || ineligible}
                    onClick={() => setApplyOpen(true)}
                  >
                    {!data.is_open ? "Applications closed" : "Apply now"}
                  </Button>
                  <Button
                    block
                    variant="secondary"
                    onClick={() => toggleSave.mutate()}
                    leftIcon={data.is_saved ? <BookmarkCheck /> : <Bookmark />}
                  >
                    {data.is_saved ? "Saved" : "Save for later"}
                  </Button>
                </div>
              )}
            </Card>

            {data.match && <MatchPanel detail={data} />}

            {data.company && (
              <Card>
                <CardHeader>
                  <CardTitle>About {data.company.name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-ink-600">
                    {data.company.industry_sector}
                    {data.company.headquarters_city
                      ? ` · ${data.company.headquarters_city}`
                      : ""}
                  </p>
                  <Link href={`/companies/${data.company.slug}`} className="mt-3 block">
                    <Button block variant="secondary" size="sm">
                      View company profile
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>

      <Dialog
        open={applyOpen}
        onClose={() => setApplyOpen(false)}
        title={`Apply: ${data.title}`}
        description={`Your application will include your skill profile as it stands today (${Math.round(data.match_score ?? 0)}% match).`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setApplyOpen(false)}>
              Cancel
            </Button>
            <Button isLoading={apply.isPending} onClick={() => apply.mutate()}>
              Submit application
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="flex gap-2 rounded-lg bg-surface-muted p-3">
            <Info className="mt-0.5 size-4 shrink-0 text-ink-400" aria-hidden />
            <p className="text-xs leading-relaxed text-ink-600">
              The recruiter sees your profile, your match score and the skills
              you meet and are missing. Being upfront about a gap and what you
              are doing about it reads better than omitting it.
            </p>
          </div>

          <Textarea
            label="Cover note (optional)"
            placeholder="Why this role, and what you have built that is relevant."
            rows={6}
            maxLength={6000}
            value={coverLetter}
            onChange={(event) => setCoverLetter(event.target.value)}
            hint={`${coverLetter.length}/6000`}
          />
        </div>
      </Dialog>
    </div>
  );
}
