"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Sparkles, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input, Select } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { SkillBadge } from "@/components/ui/skill-badge";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { PROFICIENCY_LABELS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { ProficiencyLevel, StudentSkill, TaxonomyNode } from "@/types/api";

const LEVELS: ProficiencyLevel[] = ["BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"];

export function SkillsManager() {
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Record<string, ProficiencyLevel>>({});

  const skillsQuery = useQuery({
    queryKey: ["student", "skills"],
    queryFn: () => api.get<StudentSkill[]>("/students/me/skills"),
  });

  const taxonomyQuery = useQuery({
    queryKey: ["skills", "taxonomy"],
    queryFn: () => api.get<TaxonomyNode[]>("/skills/taxonomy"),
    staleTime: 10 * 60_000,
  });

  const save = useMutation({
    mutationFn: (skills: { skill_id: string; level: ProficiencyLevel }[]) =>
      api.put<StudentSkill[]>("/students/me/skills", { skills }),
    onSuccess: () => {
      toast.success("Skills updated — your readiness has been recalculated");
      setSelected({});
      setAddOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["student"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not save skills"),
  });

  const remove = useMutation({
    mutationFn: (skillId: string) => api.delete(`/students/me/skills/${skillId}`),
    onSuccess: () => {
      toast.success("Skill removed");
      void queryClient.invalidateQueries({ queryKey: ["student"] });
    },
  });

  const owned = useMemo(
    () => new Set(skillsQuery.data?.map((entry) => entry.skill_id) ?? []),
    [skillsQuery.data],
  );

  const filteredTaxonomy = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return (taxonomyQuery.data ?? [])
      .map((node) => ({
        ...node,
        skills: node.skills.filter(
          (skill) => !owned.has(skill.id) && (!needle || skill.name.toLowerCase().includes(needle)),
        ),
      }))
      .filter((node) => node.skills.length > 0);
  }, [taxonomyQuery.data, owned, search]);

  const grouped = useMemo(() => {
    const bySource: Record<string, StudentSkill[]> = {};
    for (const entry of skillsQuery.data ?? []) {
      const key = entry.source === "ASSESSMENT" ? "Evidenced by assessment" : "Self-reported & other evidence";
      (bySource[key] ??= []).push(entry);
    }
    return bySource;
  }, [skillsQuery.data]);

  const assessed = skillsQuery.data?.filter((s) => s.source === "ASSESSMENT").length ?? 0;
  const total = skillsQuery.data?.length ?? 0;

  return (
    <>
      <PageHeader
        title="My skills"
        description="Your skill profile drives every recommendation. Skills measured by an assessment carry far more weight than self-reported ones."
        actions={
          <Button onClick={() => setAddOpen(true)} leftIcon={<Plus />}>
            Add skills
          </Button>
        }
      />

      {total > 0 && (
        <Card className="mb-5 p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-ink-900">
                {assessed} of {total} skills are backed by an assessment
              </p>
              <p className="mt-0.5 text-xs text-ink-500">
                Employers weight tested skills more heavily — and so does our matching engine.
              </p>
            </div>
            <div className="w-full max-w-xs">
              <Progress
                value={total ? (assessed / total) * 100 : 0}
                tone={assessed / Math.max(1, total) > 0.5 ? "success" : "warning"}
              />
            </div>
          </div>
        </Card>
      )}

      {skillsQuery.isLoading && <SkeletonList count={2} rows={4} />}
      {skillsQuery.error && (
        <ErrorState error={skillsQuery.error} onRetry={() => void skillsQuery.refetch()} />
      )}

      {skillsQuery.data && skillsQuery.data.length === 0 && (
        <EmptyState
          icon={<Sparkles />}
          title="No skills on your profile yet"
          description="Add the skills you have, then take an assessment to turn claims into evidence."
          action={
            <Button onClick={() => setAddOpen(true)} leftIcon={<Plus />}>
              Add your first skills
            </Button>
          }
        />
      )}

      <div className="space-y-5">
        {Object.entries(grouped).map(([group, entries]) => (
          <Card key={group}>
            <CardHeader>
              <CardTitle>{group}</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="divide-y divide-ink-100">
                {entries.map((entry) => (
                  <li key={entry.id} className="flex items-center gap-3 py-3">
                    <div className="min-w-0 flex-1">
                      <SkillBadge
                        name={entry.skill?.name ?? "Skill"}
                        level={entry.level}
                        source={entry.source}
                        confidence={entry.confidence}
                        isVerified={entry.is_verified}
                      />
                      {entry.evidence?.assessment_title ? (
                        <p className="mt-1 text-xs text-ink-500">
                          Measured in {String(entry.evidence.assessment_title)}
                          {entry.evidence.percentage
                            ? ` — ${Math.round(Number(entry.evidence.percentage))}%`
                            : ""}
                        </p>
                      ) : null}
                    </div>
                    <div className="hidden w-32 shrink-0 sm:block">
                      <Progress value={entry.score} size="sm" />
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Remove ${entry.skill?.name}`}
                      onClick={() => remove.mutate(entry.skill_id)}
                      className="text-ink-400 hover:text-danger-600"
                    >
                      <Trash2 />
                    </Button>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog
        open={addOpen}
        onClose={() => setAddOpen(false)}
        title="Add skills"
        description="Pick the skills you have and set an honest level. You can evidence them with an assessment afterwards."
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setAddOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={Object.keys(selected).length === 0}
              isLoading={save.isPending}
              onClick={() =>
                save.mutate(
                  Object.entries(selected).map(([skill_id, level]) => ({ skill_id, level })),
                )
              }
            >
              Add {Object.keys(selected).length || ""} skill
              {Object.keys(selected).length === 1 ? "" : "s"}
            </Button>
          </>
        }
      >
        <Input
          placeholder="Search skills…"
          leftIcon={<Search />}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          aria-label="Search skills"
        />

        <div className="mt-4 max-h-[46vh] space-y-4 overflow-y-auto pr-1">
          {taxonomyQuery.isLoading && <SkeletonList count={2} rows={3} />}
          {filteredTaxonomy.length === 0 && !taxonomyQuery.isLoading && (
            <p className="py-8 text-center text-sm text-ink-400">
              No skills match that search.
            </p>
          )}
          {filteredTaxonomy.map((node) => (
            <div key={node.id}>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
                {node.name}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {node.skills.slice(0, 24).map((skill) => {
                  const chosen = selected[skill.id];
                  return (
                    <div key={skill.id} className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() =>
                          setSelected((current) => {
                            const next = { ...current };
                            if (next[skill.id]) delete next[skill.id];
                            else next[skill.id] = "INTERMEDIATE";
                            return next;
                          })
                        }
                        aria-pressed={Boolean(chosen)}
                        className={cn(
                          "rounded-full border px-2.5 py-1 text-xs transition-colors",
                          chosen
                            ? "border-brand-600 bg-brand-50 font-medium text-brand-800"
                            : "border-ink-200 text-ink-700 hover:border-ink-300 hover:bg-ink-50",
                        )}
                      >
                        {skill.name}
                      </button>
                      {chosen && (
                        <select
                          aria-label={`${skill.name} level`}
                          value={chosen}
                          onChange={(event) =>
                            setSelected((current) => ({
                              ...current,
                              [skill.id]: event.target.value as ProficiencyLevel,
                            }))
                          }
                          className="rounded-md border border-ink-200 bg-surface py-1 pl-1.5 pr-6 text-2xs text-ink-700 focus:outline-none focus:ring-2 focus:ring-brand-600/30"
                        >
                          {LEVELS.map((level) => (
                            <option key={level} value={level}>
                              {PROFICIENCY_LABELS[level]}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </Dialog>
    </>
  );
}
