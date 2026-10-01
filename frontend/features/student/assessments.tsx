"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle, ArrowLeft, ArrowRight, CheckCircle2, ClipboardCheck, Clock,
  RotateCcw, XCircle,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress, ScoreRing } from "@/components/ui/progress";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  AssessmentListItem, AttemptResult, AttemptStart, Paged,
} from "@/types/api";

type Screen =
  | { mode: "list" }
  | { mode: "taking"; attempt: AttemptStart }
  | { mode: "result"; result: AttemptResult };

function Countdown({ expiresAt, onExpire }: { expiresAt?: string | null; onExpire: () => void }) {
  const [remaining, setRemaining] = useState<number | null>(null);

  useEffect(() => {
    if (!expiresAt) return;
    const tick = () => {
      const seconds = Math.max(
        0,
        Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000),
      );
      setRemaining(seconds);
      if (seconds === 0) onExpire();
    };
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [expiresAt, onExpire]);

  if (remaining === null) return null;
  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  const urgent = remaining < 120;

  return (
    <span
      role="timer"
      aria-live={urgent ? "assertive" : "off"}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-sm font-semibold tabular-nums",
        urgent ? "bg-danger-50 text-danger-700" : "bg-ink-100 text-ink-700",
      )}
    >
      <Clock className="size-4" aria-hidden />
      {minutes}:{String(seconds).padStart(2, "0")}
    </span>
  );
}

function AssessmentList({ onStart }: { onStart: (attempt: AttemptStart) => void }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["assessments"],
    queryFn: () =>
      api.paged<AssessmentListItem>("/assessments", { page_size: 30 }) as Promise<
        Paged<AssessmentListItem>
      >,
  });

  const start = useMutation({
    mutationFn: (assessmentId: string) =>
      api.post<AttemptStart>(`/assessments/${assessmentId}/attempts`),
    onSuccess: onStart,
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.message : "Could not start the assessment"),
  });

  if (isLoading) return <SkeletonList count={4} rows={3} />;
  if (error) return <ErrorState error={error} onRetry={() => void refetch()} />;
  if (!data?.data.length) {
    return (
      <EmptyState
        icon={<ClipboardCheck />}
        title="No assessments available"
        description="Assessments are published by the platform team and will appear here."
      />
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {data.data.map((assessment) => (
        <Card key={assessment.id} className="flex flex-col p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap gap-1.5">
                <Badge tone="brand">{assessment.assessment_type.replace(/_/g, " ").toLowerCase()}</Badge>
                {assessment.domain && <Badge tone="outline">{assessment.domain}</Badge>}
              </div>
              <h3 className="mt-2 text-[15px] font-semibold text-ink-900">
                {assessment.title}
              </h3>
            </div>
            {assessment.best_percentage !== null && assessment.best_percentage !== undefined && (
              <Badge tone={assessment.best_percentage >= assessment.passing_score ? "success" : "warning"} size="md">
                Best {Math.round(assessment.best_percentage)}%
              </Badge>
            )}
          </div>

          <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-ink-600">
            {assessment.description}
          </p>

          <dl className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-500">
            <div className="flex gap-1">
              <dt>Questions:</dt>
              <dd className="font-medium text-ink-700">{assessment.question_count}</dd>
            </div>
            <div className="flex gap-1">
              <dt>Time:</dt>
              <dd className="font-medium text-ink-700">{assessment.duration_minutes} min</dd>
            </div>
            <div className="flex gap-1">
              <dt>Pass mark:</dt>
              <dd className="font-medium text-ink-700">{assessment.passing_score}%</dd>
            </div>
            <div className="flex gap-1">
              <dt>Attempts:</dt>
              <dd className="font-medium text-ink-700">
                {assessment.attempts_used}/{assessment.max_attempts}
              </dd>
            </div>
          </dl>

          <div className="mt-auto pt-4">
            <Button
              block
              disabled={!assessment.can_attempt}
              isLoading={start.isPending && start.variables === assessment.id}
              onClick={() => start.mutate(assessment.id)}
              leftIcon={assessment.attempts_used > 0 ? <RotateCcw /> : <ClipboardCheck />}
            >
              {!assessment.can_attempt
                ? "No attempts left"
                : assessment.attempts_used > 0
                  ? "Retake"
                  : "Start assessment"}
            </Button>
          </div>
        </Card>
      ))}
    </div>
  );
}

function TakeAssessment({
  attempt,
  onSubmitted,
  onCancel,
}: {
  attempt: AttemptStart;
  onSubmitted: (result: AttemptResult) => void;
  onCancel: () => void;
}) {
  const queryClient = useQueryClient();
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string[]>>({});
  const question = attempt.questions[index];
  const isMulti = question?.question_type === "MULTI_CHOICE";

  const submit = useMutation({
    mutationFn: () =>
      api.post<AttemptResult>(`/assessments/attempts/${attempt.attempt_id}/submit`, {
        answers: attempt.questions.map((q) => ({
          question_id: q.id,
          selected_option_ids: answers[q.id] ?? [],
        })),
      }),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["student"] });
      void queryClient.invalidateQueries({ queryKey: ["assessments"] });
      onSubmitted(result);
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.message : "Could not submit"),
  });

  const answeredCount = Object.values(answers).filter((v) => v.length > 0).length;

  const toggle = (optionId: string) => {
    setAnswers((current) => {
      const existing = current[question.id] ?? [];
      if (isMulti) {
        return {
          ...current,
          [question.id]: existing.includes(optionId)
            ? existing.filter((id) => id !== optionId)
            : [...existing, optionId],
        };
      }
      return { ...current, [question.id]: [optionId] };
    });
  };

  if (!question) return null;

  return (
    <>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-xl font-semibold text-ink-950">
            {attempt.assessment_title}
          </h1>
          <p className="text-sm text-ink-500">
            Question {index + 1} of {attempt.total_questions} · {answeredCount} answered
          </p>
        </div>
        <Countdown
          expiresAt={attempt.expires_at}
          onExpire={() => {
            if (!submit.isPending && !submit.isSuccess) {
              toast.warning("Time is up — submitting your answers");
              submit.mutate();
            }
          }}
        />
      </div>

      <Progress
        value={((index + 1) / attempt.total_questions) * 100}
        tone="brand"
        className="mb-5"
      />

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="brand">{question.skill_name}</Badge>
            <Badge tone="outline">{question.difficulty.toLowerCase()}</Badge>
            {isMulti && <Badge tone="warning">Select all that apply</Badge>}
          </div>
          <CardTitle className="mt-2 text-base leading-relaxed">
            {question.prompt.split("```")[0].trim()}
          </CardTitle>
          {question.prompt.includes("```") && (
            <pre className="mt-3 overflow-x-auto rounded-lg bg-canvas p-4 font-mono text-xs leading-relaxed text-canvas-muted">
              {question.prompt.split("```")[1]?.replace(/^\w*\n/, "")}
            </pre>
          )}
        </CardHeader>
        <CardContent>
          <fieldset>
            <legend className="sr-only">Answer options</legend>
            <div className="space-y-2">
              {question.options.map((option) => {
                const chosen = (answers[question.id] ?? []).includes(option.id);
                return (
                  <label
                    key={option.id}
                    className={cn(
                      "flex cursor-pointer items-start gap-3 rounded-xl border p-3.5 transition-colors",
                      chosen
                        ? "border-brand-600 bg-brand-50/60 ring-1 ring-brand-600"
                        : "border-ink-200 hover:border-ink-300 hover:bg-ink-50",
                    )}
                  >
                    <input
                      type={isMulti ? "checkbox" : "radio"}
                      name={`question-${question.id}`}
                      checked={chosen}
                      onChange={() => toggle(option.id)}
                      className="mt-0.5 size-4 shrink-0 accent-brand-700"
                    />
                    <span className="text-sm leading-relaxed text-ink-800">{option.label}</span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        </CardContent>
      </Card>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <Button
          variant="secondary"
          onClick={() => setIndex((i) => Math.max(0, i - 1))}
          disabled={index === 0}
          leftIcon={<ArrowLeft />}
        >
          Previous
        </Button>

        <div className="flex gap-2">
          <Button variant="ghost" onClick={onCancel}>
            Save and exit
          </Button>
          {index === attempt.questions.length - 1 ? (
            <Button
              onClick={() => submit.mutate()}
              isLoading={submit.isPending}
              leftIcon={<CheckCircle2 />}
            >
              Submit ({answeredCount}/{attempt.total_questions})
            </Button>
          ) : (
            <Button
              onClick={() => setIndex((i) => Math.min(attempt.questions.length - 1, i + 1))}
              rightIcon={<ArrowRight />}
            >
              Next
            </Button>
          )}
        </div>
      </div>

      {/* Question jump grid — lets a candidate revisit anything before submitting. */}
      <div className="mt-6">
        <p className="mb-2 text-xs font-medium text-ink-500">Jump to question</p>
        <div className="flex flex-wrap gap-1.5">
          {attempt.questions.map((q, i) => {
            const answered = (answers[q.id] ?? []).length > 0;
            return (
              <button
                key={q.id}
                type="button"
                onClick={() => setIndex(i)}
                aria-label={`Question ${i + 1}${answered ? ", answered" : ", unanswered"}`}
                aria-current={i === index ? "true" : undefined}
                className={cn(
                  "size-8 rounded-lg border text-xs font-medium transition-colors",
                  i === index
                    ? "border-brand-700 bg-brand-700 text-white"
                    : answered
                      ? "border-success-500/40 bg-success-50 text-success-700"
                      : "border-ink-200 bg-surface text-ink-500 hover:border-ink-300",
                )}
              >
                {i + 1}
              </button>
            );
          })}
        </div>
      </div>
    </>
  );
}

function AssessmentResult({
  result,
  onDone,
}: {
  result: AttemptResult;
  onDone: () => void;
}) {
  const wrong = result.answers.filter((answer) => !answer.is_correct);

  return (
    <>
      <PageHeader
        title={result.assessment_title}
        description="Your results, and what changed on your profile as a result."
        actions={
          <>
            <Button variant="secondary" onClick={onDone}>
              Back to assessments
            </Button>
            <Link href="/student/skill-gap">
              <Button rightIcon={<ArrowRight />}>See your updated gap</Button>
            </Link>
          </>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardContent className="flex flex-col items-center gap-4 pt-6">
            <ScoreRing value={result.percentage} size={150} sublabel="score" />
            <Badge tone={result.is_passed ? "success" : "warning"} size="md">
              {result.is_passed ? "Passed" : "Not passed"}
            </Badge>
            <p className="text-center text-sm leading-relaxed text-ink-600">
              {result.feedback}
            </p>
            <dl className="w-full space-y-1.5 border-t border-ink-100 pt-4 text-xs">
              <div className="flex justify-between">
                <dt className="text-ink-500">Raw score</dt>
                <dd className="font-medium tabular-nums text-ink-800">
                  {result.raw_score} / {result.max_score}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-ink-500">Confidence</dt>
                <dd className="font-medium tabular-nums text-ink-800">
                  {Math.round(result.confidence * 100)}%
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-ink-500">Attempt</dt>
                <dd className="font-medium tabular-nums text-ink-800">
                  #{result.attempt_number}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Per-skill breakdown</CardTitle>
            <p className="text-sm text-ink-500">
              These levels were written to your skill profile, replacing any self-reported claim.
            </p>
          </CardHeader>
          <CardContent>
            <ul className="divide-y divide-ink-100">
              {result.skill_scores.map((score) => (
                <li key={score.skill_id} className="flex items-center gap-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink-900">
                      {score.skill_name}
                    </p>
                    <p className="text-xs text-ink-500">
                      {score.correct_count}/{score.questions_count} correct · now{" "}
                      <strong className="font-medium text-ink-700">
                        {score.level.toLowerCase()}
                      </strong>
                    </p>
                  </div>
                  <div className="w-28 shrink-0">
                    <Progress value={score.percentage} size="sm" showValue />
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      {wrong.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Review what you missed</CardTitle>
            <p className="text-sm text-ink-500">
              {wrong.length} question{wrong.length === 1 ? "" : "s"} to learn from.
            </p>
          </CardHeader>
          <CardContent>
            <ul className="space-y-4">
              {wrong.map((answer) => (
                <li
                  key={answer.question_id}
                  className="rounded-xl border border-ink-200 p-4"
                >
                  <div className="flex items-start gap-2.5">
                    <XCircle className="mt-0.5 size-4 shrink-0 text-danger-500" aria-hidden />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink-900">
                        {answer.prompt.split("```")[0].trim()}
                      </p>
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        <Badge tone="outline">{answer.skill_name}</Badge>
                        <Badge tone="neutral">{answer.difficulty.toLowerCase()}</Badge>
                      </div>
                      {answer.explanation && (
                        <div className="mt-2.5 flex gap-2 rounded-lg bg-brand-50/70 p-3">
                          <AlertCircle className="mt-0.5 size-4 shrink-0 text-brand-700" aria-hidden />
                          <p className="text-xs leading-relaxed text-brand-900">
                            {answer.explanation}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </>
  );
}

export function Assessments() {
  const [screen, setScreen] = useState<Screen>({ mode: "list" });

  if (screen.mode === "taking") {
    return (
      <TakeAssessment
        attempt={screen.attempt}
        onSubmitted={(result) => setScreen({ mode: "result", result })}
        onCancel={() => setScreen({ mode: "list" })}
      />
    );
  }

  if (screen.mode === "result") {
    return (
      <AssessmentResult
        result={screen.result}
        onDone={() => setScreen({ mode: "list" })}
      />
    );
  }

  return (
    <>
      <PageHeader
        title="Skill assessments"
        description="Turn claims into evidence. Results write measured levels straight into your skill profile, which sharpens every recommendation."
      />
      <AssessmentList onStart={(attempt) => setScreen({ mode: "taking", attempt })} />
    </>
  );
}
