"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input, Select, Textarea } from "@/components/ui/input";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { LearningProgram, Paged, SkillBrief } from "@/types/api";

export function IndustryPrograms() {
  const queryClient = useQueryClient();
  const { session } = useAuth();
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({
    title: "", summary: "", description: "", program_type: "COURSE",
    difficulty: "MEDIUM", duration_hours: 12, price_amount: 0,
  });
  const [skillIds, setSkillIds] = useState<string[]>([]);

  const programs = useQuery({
    queryKey: ["industry", "programs"],
    queryFn: () =>
      api.paged<LearningProgram>("/learning/programs", {
        company_id: session?.user.company_id ?? undefined,
        page_size: 40,
      }) as Promise<Paged<LearningProgram>>,
    enabled: Boolean(session?.user.company_id),
  });

  const skills = useQuery({
    queryKey: ["skills", "program-picker"],
    queryFn: () =>
      api.paged<SkillBrief>("/skills", { page_size: 60, sort_by: "demand_score" }),
    staleTime: 10 * 60_000,
  });

  const create = useMutation({
    mutationFn: () =>
      api.post<LearningProgram>("/learning/programs", {
        ...form,
        duration_hours: Number(form.duration_hours),
        price_amount: Number(form.price_amount),
        skills: skillIds.map((id) => ({
          skill_id: id,
          target_level: "INTERMEDIATE",
          coverage_weight: 1,
        })),
      }),
    onSuccess: () => {
      toast.success("Programme published");
      setCreateOpen(false);
      setSkillIds([]);
      void queryClient.invalidateQueries({ queryKey: ["industry", "programs"] });
      void queryClient.invalidateQueries({ queryKey: ["learning"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not publish"),
  });

  return (
    <>
      <PageHeader
        title="Learning programmes"
        description="Training you publish for students. Tagging the skills a programme teaches is what lets us recommend it to the students whose gaps it actually closes."
        actions={
          <Button onClick={() => setCreateOpen(true)} leftIcon={<Plus />}>
            Publish a programme
          </Button>
        }
      />

      {programs.isLoading && <SkeletonList count={3} rows={2} />}
      {programs.error && (
        <ErrorState error={programs.error} onRetry={() => void programs.refetch()} />
      )}
      {programs.data?.data.length === 0 && (
        <EmptyState
          icon={<BookOpen />}
          title="No programmes published"
          description="Publish training and it will be recommended to students whose skill gaps it closes."
          action={
            <Button size="sm" onClick={() => setCreateOpen(true)} leftIcon={<Plus />}>
              Publish your first
            </Button>
          }
        />
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {programs.data?.data.map((program) => (
          <Card key={program.id} className="p-5">
            <div className="flex flex-wrap gap-1.5">
              <Badge tone="brand">
                {program.program_type.replace(/_/g, " ").toLowerCase()}
              </Badge>
              <Badge tone="outline">{program.difficulty.toLowerCase()}</Badge>
              {program.is_free && <Badge tone="success">Free</Badge>}
            </div>
            <h3 className="mt-2 text-[15px] font-semibold text-ink-900">{program.title}</h3>
            <p className="mt-1 line-clamp-2 text-sm text-ink-600">{program.summary}</p>
            <div className="mt-3 flex flex-wrap gap-1">
              {program.skills.slice(0, 5).map((entry) => (
                <Badge key={entry.skill_id} tone="neutral">{entry.skill?.name}</Badge>
              ))}
            </div>
            <p className="mt-3 border-t border-ink-100 pt-3 text-xs text-ink-500">
              {program.duration_hours}h · {program.enrollment_count} enrolled
            </p>
          </Card>
        ))}
      </div>

      <Dialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Publish a learning programme"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button
              disabled={form.title.length < 3 || skillIds.length === 0}
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
          <Input
            label="Summary"
            hint="One line, shown on cards."
            value={form.summary}
            onChange={(event) => setForm((c) => ({ ...c, summary: event.target.value }))}
          />
          <Textarea
            label="Description"
            rows={4}
            value={form.description}
            onChange={(event) => setForm((c) => ({ ...c, description: event.target.value }))}
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <Select
              label="Type"
              value={form.program_type}
              onChange={(event) =>
                setForm((c) => ({ ...c, program_type: event.target.value }))
              }
            >
              {["COURSE", "CERTIFICATION", "WORKSHOP", "BOOTCAMP", "TRAINING", "MENTORSHIP_PROGRAM"].map(
                (item) => (
                  <option key={item} value={item}>
                    {item.replace(/_/g, " ").toLowerCase()}
                  </option>
                ),
              )}
            </Select>
            <Select
              label="Difficulty"
              value={form.difficulty}
              onChange={(event) => setForm((c) => ({ ...c, difficulty: event.target.value }))}
            >
              <option value="EASY">Easy</option>
              <option value="MEDIUM">Medium</option>
              <option value="HARD">Hard</option>
            </Select>
            <Input
              label="Duration (hours)"
              type="number"
              min={1}
              value={form.duration_hours}
              onChange={(event) =>
                setForm((c) => ({ ...c, duration_hours: Number(event.target.value) }))
              }
            />
            <Input
              label="Price (0 for free)"
              type="number"
              min={0}
              value={form.price_amount}
              onChange={(event) =>
                setForm((c) => ({ ...c, price_amount: Number(event.target.value) }))
              }
            />
          </div>

          <div>
            <p className="mb-2 text-sm font-medium text-ink-800">
              Skills this teaches <span className="text-danger-600">*</span>
            </p>
            <div className="max-h-44 overflow-y-auto rounded-lg border border-ink-200 p-2">
              <div className="flex flex-wrap gap-1.5">
                {skills.data?.data.map((skill) => {
                  const chosen = skillIds.includes(skill.id);
                  return (
                    <button
                      key={skill.id}
                      type="button"
                      onClick={() =>
                        setSkillIds((current) =>
                          chosen
                            ? current.filter((id) => id !== skill.id)
                            : [...current, skill.id],
                        )
                      }
                      aria-pressed={chosen}
                      className={
                        chosen
                          ? "rounded-full border border-brand-600 bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-800"
                          : "rounded-full border border-ink-200 px-2.5 py-1 text-xs text-ink-700 hover:bg-ink-50"
                      }
                    >
                      {skill.name}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </Dialog>
    </>
  );
}
