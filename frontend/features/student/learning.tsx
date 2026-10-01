"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Award, BookOpen, Check, Clock, GraduationCap, Sparkles } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import type {
  Enrollment, LearningProgram, LearningRecommendation, Paged,
} from "@/types/api";

function ProgramCard({
  program,
  onEnroll,
  isEnrolling,
  reason,
}: {
  program: LearningProgram;
  onEnroll?: (id: string) => void;
  isEnrolling?: boolean;
  reason?: string;
}) {
  return (
    <Card className="flex flex-col p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap gap-1.5">
            <Badge tone="brand">{program.program_type.replace(/_/g, " ").toLowerCase()}</Badge>
            <Badge tone="outline">{program.difficulty.toLowerCase()}</Badge>
            {program.is_free && <Badge tone="success">Free</Badge>}
            {program.grants_certificate && <Badge tone="accent">Certificate</Badge>}
          </div>
          <h3 className="mt-2 text-[15px] font-semibold text-ink-900">{program.title}</h3>
          <p className="mt-0.5 text-xs text-ink-500">
            {program.provider_name ?? program.company?.name}
          </p>
        </div>
      </div>

      <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-ink-600">
        {program.summary}
      </p>

      {reason && (
        <p className="mt-2 rounded-lg bg-brand-50/70 px-3 py-2 text-xs leading-relaxed text-brand-900">
          {reason}
        </p>
      )}

      {program.skills.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {program.skills.slice(0, 4).map((entry) => (
            <Badge key={entry.skill_id} tone="neutral">{entry.skill?.name}</Badge>
          ))}
        </div>
      )}

      <div className="mt-auto flex items-center justify-between gap-3 border-t border-ink-100 pt-3.5 mt-4">
        <div className="text-xs text-ink-500">
          <span className="inline-flex items-center gap-1">
            <Clock className="size-3.5" aria-hidden />
            {program.duration_hours}h
          </span>
          <span className="mx-2">·</span>
          <span>{program.is_free ? "Free" : formatCurrency(program.price_amount, program.currency)}</span>
        </div>
        {program.is_enrolled ? (
          <Badge tone="success" size="md">
            <Check className="size-3" aria-hidden />
            Enrolled
          </Badge>
        ) : (
          onEnroll && (
            <Button size="sm" isLoading={isEnrolling} onClick={() => onEnroll(program.id)}>
              Enrol
            </Button>
          )
        )}
      </div>
    </Card>
  );
}

export function StudentLearning() {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [type, setType] = useState("");

  const recommendations = useQuery({
    queryKey: ["recommendations", "learning"],
    queryFn: () =>
      api.get<LearningRecommendation[]>("/recommendations/learning", { limit: 6 }),
  });

  const programs = useQuery({
    queryKey: ["learning", "programs", search, type],
    queryFn: () =>
      api.paged<LearningProgram>("/learning/programs", {
        q: search || undefined,
        program_type: type || undefined,
        page_size: 24,
      }) as Promise<Paged<LearningProgram>>,
  });

  const enrollments = useQuery({
    queryKey: ["learning", "enrollments"],
    queryFn: () =>
      api.paged<Enrollment>("/learning/enrollments", { page_size: 30 }) as Promise<
        Paged<Enrollment>
      >,
  });

  const enroll = useMutation({
    mutationFn: (programId: string) =>
      api.post<Enrollment>(`/learning/programs/${programId}/enroll`),
    onSuccess: () => {
      toast.success("Enrolled — it's now in your learning tab");
      void queryClient.invalidateQueries({ queryKey: ["learning"] });
      void queryClient.invalidateQueries({ queryKey: ["student"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not enrol"),
  });

  return (
    <>
      <PageHeader
        title="Learning programmes"
        description="Courses, certifications and bootcamps from industry partners — recommended against the gaps that actually matter for your target role."
      />

      <Tabs defaultValue="recommended">
        <TabsList ariaLabel="Learning views">
          <TabsTrigger value="recommended">Recommended for you</TabsTrigger>
          <TabsTrigger value="browse">Browse all</TabsTrigger>
          <TabsTrigger value="enrolled">
            My learning
            {enrollments.data?.meta.total ? ` (${enrollments.data.meta.total})` : ""}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="recommended">
          {recommendations.isLoading && <SkeletonList count={3} rows={3} />}
          {recommendations.error && (
            <ErrorState
              error={recommendations.error}
              onRetry={() => void recommendations.refetch()}
            />
          )}
          {recommendations.data?.length === 0 && (
            <EmptyState
              icon={<Sparkles />}
              title="No recommendations yet"
              description="Set a target role and add a few skills — we'll then recommend programmes that close your specific gaps."
            />
          )}
          {recommendations.data && recommendations.data.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {recommendations.data.map((item) => (
                <Card key={item.target_id} className="flex flex-col p-5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex flex-wrap gap-1.5">
                        <Badge tone="brand">
                          {item.program_type.replace(/_/g, " ").toLowerCase()}
                        </Badge>
                        {item.is_free && <Badge tone="success">Free</Badge>}
                      </div>
                      <h3 className="mt-2 text-[15px] font-semibold text-ink-900">
                        {item.target_title}
                      </h3>
                      <p className="text-xs text-ink-500">{item.provider}</p>
                    </div>
                    <Badge tone="accent" size="md">
                      {Math.round(item.match_score)}%
                    </Badge>
                  </div>

                  <p className="mt-2 text-xs leading-relaxed text-ink-600">
                    {item.reason_summary}
                  </p>

                  <div className="mt-2.5 flex flex-wrap gap-1">
                    {item.matching_skills.slice(0, 4).map((skill) => (
                      <Badge key={skill} tone="neutral">{skill}</Badge>
                    ))}
                  </div>

                  <div className="mt-auto flex items-center justify-between gap-3 border-t border-ink-100 pt-3.5 mt-4">
                    <span className="inline-flex items-center gap-1 text-xs text-ink-500">
                      <Clock className="size-3.5" aria-hidden />
                      {item.duration_hours}h
                    </span>
                    <Button
                      size="sm"
                      isLoading={enroll.isPending && enroll.variables === item.target_id}
                      onClick={() => enroll.mutate(item.target_id)}
                    >
                      Enrol
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="browse">
          <Card className="mb-4 p-4">
            <form
              onSubmit={(event) => {
                event.preventDefault();
                setSearch(query);
              }}
              className="flex flex-wrap items-end gap-3"
            >
              <div className="min-w-[14rem] flex-1">
                <Input
                  label="Search programmes"
                  placeholder="e.g. Docker, machine learning"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </div>
              <Select
                label="Type"
                value={type}
                onChange={(event) => setType(event.target.value)}
                className="w-48"
              >
                <option value="">All types</option>
                <option value="COURSE">Course</option>
                <option value="CERTIFICATION">Certification</option>
                <option value="WORKSHOP">Workshop</option>
                <option value="BOOTCAMP">Bootcamp</option>
                <option value="TRAINING">Training</option>
              </Select>
              <Button type="submit">Search</Button>
            </form>
          </Card>

          {programs.isLoading && <SkeletonList count={6} rows={3} />}
          {programs.error && (
            <ErrorState error={programs.error} onRetry={() => void programs.refetch()} />
          )}
          {programs.data?.data.length === 0 && (
            <EmptyState
              icon={<BookOpen />}
              title="No programmes match"
              description="Try a different search term or clear the type filter."
            />
          )}
          {programs.data && programs.data.data.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {programs.data.data.map((program) => (
                <ProgramCard
                  key={program.id}
                  program={program}
                  onEnroll={(id) => enroll.mutate(id)}
                  isEnrolling={enroll.isPending && enroll.variables === program.id}
                />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="enrolled">
          {enrollments.isLoading && <SkeletonList count={3} rows={2} />}
          {enrollments.data?.data.length === 0 && (
            <EmptyState
              icon={<GraduationCap />}
              title="You're not enrolled in anything yet"
              description="Enrol in a recommended programme to start closing your highest-priority gaps."
            />
          )}
          {enrollments.data && enrollments.data.data.length > 0 && (
            <div className="space-y-3">
              {enrollments.data.data.map((enrollment) => (
                <Card key={enrollment.id} className="p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="truncate text-[15px] font-semibold text-ink-900">
                        {enrollment.program?.title}
                      </h3>
                      <p className="text-xs text-ink-500">
                        {enrollment.program?.provider_name} · {enrollment.program?.duration_hours}h
                      </p>
                    </div>
                    <Badge
                      tone={
                        enrollment.status === "COMPLETED"
                          ? "success"
                          : enrollment.status === "IN_PROGRESS"
                            ? "brand"
                            : "neutral"
                      }
                      size="md"
                    >
                      {enrollment.status.replace(/_/g, " ").toLowerCase()}
                    </Badge>
                  </div>
                  <div className="mt-3">
                    <Progress
                      value={enrollment.progress_percentage}
                      label="Progress"
                      showValue
                      tone={enrollment.progress_percentage === 100 ? "success" : "brand"}
                    />
                  </div>
                  {enrollment.status === "COMPLETED" && (
                    <p className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-success-700">
                      <Award className="size-3.5" aria-hidden />
                      Certificate issued and skills credited to your profile
                    </p>
                  )}
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </>
  );
}
