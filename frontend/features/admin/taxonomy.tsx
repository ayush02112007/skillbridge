"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, RefreshCw, Search, Sparkles, Target } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input, Select, Textarea } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TBody, TD, TH, THead, TR, Table, TableWrapper } from "@/components/ui/table";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import type { JobRole, Paged, Skill, SkillCategory, TaxonomyNode } from "@/types/api";

export function AdminTaxonomy() {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ name: "", category_id: "", description: "", aliases: "" });

  const skills = useQuery({
    queryKey: ["admin", "skills", search],
    queryFn: () =>
      api.paged<Skill>("/skills", {
        q: search || undefined,
        page_size: 50,
        sort_by: "demand_score",
      }) as Promise<Paged<Skill>>,
  });

  const taxonomy = useQuery({
    queryKey: ["skills", "taxonomy"],
    queryFn: () => api.get<TaxonomyNode[]>("/skills/taxonomy"),
  });

  const categories = useQuery({
    queryKey: ["skills", "categories"],
    queryFn: () => api.get<SkillCategory[]>("/skills/categories"),
  });

  const roles = useQuery({
    queryKey: ["admin", "job-roles"],
    queryFn: () => api.paged<JobRole>("/job-roles", { page_size: 60 }) as Promise<Paged<JobRole>>,
  });

  const createSkill = useMutation({
    mutationFn: () =>
      api.post<Skill>("/skills", {
        name: form.name,
        category_id: form.category_id,
        description: form.description,
        aliases: form.aliases
          ? form.aliases.split(",").map((a) => a.trim()).filter(Boolean)
          : [],
      }),
    onSuccess: () => {
      toast.success("Skill added to the taxonomy");
      setCreateOpen(false);
      setForm({ name: "", category_id: "", description: "", aliases: "" });
      void queryClient.invalidateQueries({ queryKey: ["skills"] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "skills"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not add the skill"),
  });

  const refreshDemand = useMutation({
    mutationFn: () =>
      api.post<{ skills_updated: number }>("/admin/maintenance/refresh-skill-demand"),
    onSuccess: (result) => {
      toast.success(`Demand recomputed for ${result.skills_updated} skills`);
      void queryClient.invalidateQueries({ queryKey: ["skills"] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "skills"] });
    },
  });

  return (
    <>
      <PageHeader
        title="Skills & roles"
        description="The taxonomy every recommendation depends on. Adding a skill here makes it immediately available to students, recruiters and the matching engine."
        actions={
          <>
            <Button
              variant="secondary"
              leftIcon={<RefreshCw />}
              isLoading={refreshDemand.isPending}
              onClick={() => refreshDemand.mutate()}
            >
              Recompute demand
            </Button>
            <Button onClick={() => setCreateOpen(true)} leftIcon={<Plus />}>
              Add skill
            </Button>
          </>
        }
      />

      <Tabs defaultValue="skills">
        <TabsList ariaLabel="Taxonomy views">
          <TabsTrigger value="skills">Skills</TabsTrigger>
          <TabsTrigger value="categories">Categories</TabsTrigger>
          <TabsTrigger value="roles">Job roles</TabsTrigger>
        </TabsList>

        <TabsContent value="skills">
          <Card className="mb-4 p-4">
            <form
              onSubmit={(event) => {
                event.preventDefault();
                setSearch(query);
              }}
              className="flex items-end gap-3"
            >
              <div className="flex-1">
                <Input
                  label="Search skills"
                  leftIcon={<Search />}
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </div>
              <Button type="submit">Search</Button>
            </form>
          </Card>

          {skills.isLoading && <SkeletonList count={4} rows={1} />}
          {skills.error && (
            <ErrorState error={skills.error} onRetry={() => void skills.refetch()} />
          )}
          {skills.data && (
            <>
              <p className="mb-3 text-sm text-ink-500">{skills.data.meta.total} skills</p>
              <TableWrapper caption="Skills">
                <Table>
                  <THead>
                    <TR>
                      <TH>Skill</TH>
                      <TH>Category</TH>
                      <TH>Aliases</TH>
                      <TH>Market demand</TH>
                      <TH>Flags</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {skills.data.data.map((skill) => (
                      <TR key={skill.id}>
                        <TD className="font-medium text-ink-900">{skill.name}</TD>
                        <TD className="text-xs">{skill.category?.name ?? "—"}</TD>
                        <TD className="max-w-xs truncate text-2xs text-ink-500">
                          {skill.aliases.join(", ") || "—"}
                        </TD>
                        <TD>
                          <div className="w-28">
                            <Progress value={skill.demand_score} size="sm" showValue />
                          </div>
                        </TD>
                        <TD>
                          <div className="flex gap-1">
                            {skill.is_trending && <Badge tone="accent">Trending</Badge>}
                            {skill.is_soft_skill && <Badge tone="neutral">Soft</Badge>}
                          </div>
                        </TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </TableWrapper>
            </>
          )}
        </TabsContent>

        <TabsContent value="categories">
          {taxonomy.isLoading && <SkeletonList count={4} rows={2} />}
          <div className="grid gap-4 md:grid-cols-2">
            {taxonomy.data?.map((node) => (
              <Card key={node.id}>
                <CardHeader className="flex-row items-center gap-2">
                  <CardTitle className="flex-1">{node.name}</CardTitle>
                  <Badge tone="neutral">{node.skill_count} skills</Badge>
                  {node.is_soft_skill && <Badge tone="outline">Soft skills</Badge>}
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-1">
                    {node.skills.slice(0, 14).map((skill) => (
                      <Badge key={skill.id} tone="neutral">{skill.name}</Badge>
                    ))}
                    {node.skills.length > 14 && (
                      <Badge tone="outline">+{node.skills.length - 14} more</Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="roles">
          {roles.isLoading && <SkeletonList count={4} rows={2} />}
          {roles.data?.data.length === 0 && (
            <EmptyState icon={<Target />} title="No job roles configured" />
          )}
          <div className="space-y-3">
            {roles.data?.data.map((role) => (
              <Card key={role.id} className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[15px] font-semibold text-ink-900">{role.title}</p>
                    <p className="text-xs text-ink-500">
                      {role.family} · {role.seniority.toLowerCase()} ·{" "}
                      {role.required_skills.length} skill requirements
                    </p>
                    <p className="mt-1.5 line-clamp-2 text-sm text-ink-600">
                      {role.description}
                    </p>
                  </div>
                  <Badge tone="brand" size="md">
                    Demand {Math.round(role.demand_index)}
                  </Badge>
                </div>
                <div className="mt-3 flex flex-wrap gap-1">
                  {role.required_skills.slice(0, 10).map((requirement) => (
                    <Badge
                      key={requirement.skill_id}
                      tone={requirement.importance === "REQUIRED" ? "brand" : "neutral"}
                    >
                      {requirement.skill?.name} · {requirement.required_level.toLowerCase()}
                    </Badge>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      <Dialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Add a skill"
        description="Aliases matter: they are what the resume and job-description extractors match against."
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button
              disabled={!form.name || !form.category_id}
              isLoading={createSkill.isPending}
              onClick={() => createSkill.mutate()}
            >
              Add skill
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Input
            label="Skill name"
            required
            placeholder="Apache Kafka"
            value={form.name}
            onChange={(event) => setForm((c) => ({ ...c, name: event.target.value }))}
          />
          <Select
            label="Category"
            required
            value={form.category_id}
            onChange={(event) => setForm((c) => ({ ...c, category_id: event.target.value }))}
          >
            <option value="">Select a category</option>
            {categories.data?.map((category) => (
              <option key={category.id} value={category.id}>{category.name}</option>
            ))}
          </Select>
          <Input
            label="Aliases"
            hint="Comma separated, e.g. kafka, event streaming"
            value={form.aliases}
            onChange={(event) => setForm((c) => ({ ...c, aliases: event.target.value }))}
          />
          <Textarea
            label="Description"
            rows={3}
            value={form.description}
            onChange={(event) => setForm((c) => ({ ...c, description: event.target.value }))}
          />
        </div>
      </Dialog>
    </>
  );
}
