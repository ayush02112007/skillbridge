"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Save, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input, Select, Textarea } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState, ErrorState, SkeletonCard } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type {
  Institution, JobRole, Paged, ProfileCompletion, StudentProfile,
} from "@/types/api";

type SubResource = "education" | "experience" | "projects" | "achievements";

const SUB_FIELDS: Record<SubResource, { name: string; label: string; type?: string; required?: boolean }[]> = {
  education: [
    { name: "level", label: "Level", type: "select", required: true },
    { name: "institution_name", label: "Institution", required: true },
    { name: "program", label: "Programme" },
    { name: "start_year", label: "Start year", type: "number", required: true },
    { name: "end_year", label: "End year", type: "number" },
    { name: "score_value", label: "Score", type: "number" },
    { name: "score_type", label: "Score type", type: "scoretype" },
  ],
  experience: [
    { name: "title", label: "Title", required: true },
    { name: "organization", label: "Organisation", required: true },
    { name: "kind", label: "Type", type: "kind" },
    { name: "location", label: "Location" },
    { name: "start_date", label: "Start date", type: "date" },
    { name: "end_date", label: "End date", type: "date" },
    { name: "description", label: "What you did", type: "textarea" },
  ],
  projects: [
    { name: "title", label: "Title", required: true },
    { name: "role", label: "Your role" },
    { name: "description", label: "Description", type: "textarea" },
    { name: "repository_url", label: "Repository URL" },
    { name: "demo_url", label: "Demo URL" },
  ],
  achievements: [
    { name: "title", label: "Title", required: true },
    { name: "category", label: "Category", type: "achievementcategory" },
    { name: "issuer", label: "Issued by" },
    { name: "position", label: "Position" },
    { name: "achieved_on", label: "Date", type: "date" },
  ],
};

function SubResourceManager({ resource }: { resource: SubResource }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({});

  const list = useQuery({
    queryKey: ["student", resource],
    queryFn: () => api.get<Record<string, unknown>[]>(`/students/me/${resource}`),
  });

  const create = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.post(`/students/me/${resource}`, payload),
    onSuccess: () => {
      toast.success("Added");
      setOpen(false);
      setForm({});
      void queryClient.invalidateQueries({ queryKey: ["student"] });
    },
    onError: (error) => {
      const message = error instanceof ApiError
        ? Object.values(error.fieldErrors)[0] ?? error.message
        : "Could not save";
      toast.error(message);
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.delete(`/students/me/${resource}/${id}`),
    onSuccess: () => {
      toast.success("Removed");
      void queryClient.invalidateQueries({ queryKey: ["student"] });
    },
  });

  const submit = () => {
    const payload: Record<string, unknown> = {};
    for (const field of SUB_FIELDS[resource]) {
      const value = form[field.name];
      if (value === undefined || value === "") continue;
      payload[field.name] =
        field.type === "number" ? Number(value) : value;
    }
    // Defaults the API expects.
    if (resource === "education" && !payload.score_type) payload.score_type = "PERCENTAGE";
    if (resource === "experience" && !payload.kind) payload.kind = "INTERNSHIP";
    if (resource === "achievements" && !payload.category) payload.category = "COMPETITION";
    if (resource === "projects") payload.team_size = payload.team_size ?? 1;
    create.mutate(payload);
  };

  return (
    <>
      <div className="mb-3 flex justify-end">
        <Button size="sm" onClick={() => setOpen(true)} leftIcon={<Plus />}>
          Add {resource.replace(/s$/, "")}
        </Button>
      </div>

      {list.isLoading && <SkeletonCard rows={3} />}
      {list.error && <ErrorState error={list.error} onRetry={() => void list.refetch()} />}

      {list.data?.length === 0 && (
        <EmptyState
          title={`No ${resource} added`}
          description="Adding these raises your profile completion and improves matching."
          action={
            <Button size="sm" onClick={() => setOpen(true)} leftIcon={<Plus />}>
              Add your first
            </Button>
          }
        />
      )}

      {list.data && list.data.length > 0 && (
        <ul className="space-y-2">
          {list.data.map((entry) => (
            <li
              key={String(entry.id)}
              className="flex items-start justify-between gap-3 rounded-xl border border-ink-200 bg-surface p-4"
            >
              <div className="min-w-0">
                <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink-900">
                  {String(entry.title ?? entry.program ?? entry.institution_name ?? "Entry")}
                  {Boolean(entry.is_verified) && <Badge tone="success">Verified</Badge>}
                </p>
                <p className="text-xs text-ink-500">
                  {String(entry.organization ?? entry.institution_name ?? entry.issuer ?? "")}
                  {entry.start_year ? ` · ${entry.start_year}–${entry.end_year ?? ""}` : ""}
                  {entry.start_date ? ` · ${formatDate(String(entry.start_date))}` : ""}
                </p>
                {Boolean(entry.description) && (
                  <p className="mt-1 line-clamp-2 text-xs text-ink-600">
                    {String(entry.description)}
                  </p>
                )}
              </div>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Remove entry"
                onClick={() => remove.mutate(String(entry.id))}
                className="text-ink-400 hover:text-danger-600"
              >
                <Trash2 />
              </Button>
            </li>
          ))}
        </ul>
      )}

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title={`Add ${resource.replace(/s$/, "")}`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button isLoading={create.isPending} onClick={submit}>Save</Button>
          </>
        }
      >
        <div className="space-y-3">
          {SUB_FIELDS[resource].map((field) => {
            const value = form[field.name] ?? "";
            const onChange = (v: string) =>
              setForm((current) => ({ ...current, [field.name]: v }));

            if (field.type === "textarea") {
              return (
                <Textarea
                  key={field.name}
                  label={field.label}
                  rows={3}
                  value={value}
                  onChange={(event) => onChange(event.target.value)}
                />
              );
            }
            if (field.type === "select") {
              return (
                <Select
                  key={field.name}
                  label={field.label}
                  required={field.required}
                  value={value}
                  onChange={(event) => onChange(event.target.value)}
                >
                  <option value="">Select…</option>
                  {["SECONDARY", "HIGHER_SECONDARY", "DIPLOMA", "BACHELORS", "MASTERS", "DOCTORATE"].map(
                    (level) => (
                      <option key={level} value={level}>
                        {level.replace(/_/g, " ").toLowerCase()}
                      </option>
                    ),
                  )}
                </Select>
              );
            }
            if (field.type === "scoretype") {
              return (
                <Select
                  key={field.name}
                  label={field.label}
                  value={value || "PERCENTAGE"}
                  onChange={(event) => onChange(event.target.value)}
                >
                  <option value="PERCENTAGE">Percentage</option>
                  <option value="CGPA">CGPA</option>
                  <option value="GRADE">Grade</option>
                </Select>
              );
            }
            if (field.type === "kind") {
              return (
                <Select
                  key={field.name}
                  label={field.label}
                  value={value || "INTERNSHIP"}
                  onChange={(event) => onChange(event.target.value)}
                >
                  {["INTERNSHIP", "JOB", "RESEARCH", "VOLUNTEERING", "FREELANCE"].map((kind) => (
                    <option key={kind} value={kind}>{kind.toLowerCase()}</option>
                  ))}
                </Select>
              );
            }
            if (field.type === "achievementcategory") {
              return (
                <Select
                  key={field.name}
                  label={field.label}
                  value={value || "COMPETITION"}
                  onChange={(event) => onChange(event.target.value)}
                >
                  {["COMPETITION", "HACKATHON", "SCHOLARSHIP", "LEADERSHIP", "VOLUNTEERING", "PUBLICATION"].map(
                    (category) => (
                      <option key={category} value={category}>
                        {category.toLowerCase()}
                      </option>
                    ),
                  )}
                </Select>
              );
            }
            return (
              <Input
                key={field.name}
                label={field.label}
                type={field.type ?? "text"}
                required={field.required}
                value={value}
                onChange={(event) => onChange(event.target.value)}
              />
            );
          })}
        </div>
      </Dialog>
    </>
  );
}

export function StudentProfileEditor() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<Partial<StudentProfile>>({});

  const profile = useQuery({
    queryKey: ["student", "profile"],
    queryFn: () => api.get<StudentProfile>("/students/me"),
  });

  const completion = useQuery({
    queryKey: ["student", "completion"],
    queryFn: () => api.get<ProfileCompletion>("/students/me/completion"),
  });

  const institutions = useQuery({
    queryKey: ["institutions", "list"],
    queryFn: () => api.paged<Institution>("/institutions", { page_size: 60 }) as Promise<Paged<Institution>>,
    staleTime: 10 * 60_000,
  });

  const roles = useQuery({
    queryKey: ["job-roles", "profile"],
    queryFn: () => api.paged<JobRole>("/job-roles", { page_size: 60 }) as Promise<Paged<JobRole>>,
    staleTime: 10 * 60_000,
  });

  useEffect(() => {
    if (profile.data) setForm(profile.data);
  }, [profile.data]);

  const save = useMutation({
    mutationFn: (payload: Partial<StudentProfile>) =>
      api.patch<StudentProfile>("/students/me", payload),
    onSuccess: () => {
      toast.success("Profile saved");
      void queryClient.invalidateQueries({ queryKey: ["student"] });
    },
    onError: (error) => {
      const message = error instanceof ApiError
        ? Object.values(error.fieldErrors)[0] ?? error.message
        : "Could not save";
      toast.error(message);
    },
  });

  const set = <K extends keyof StudentProfile>(key: K, value: StudentProfile[K]) =>
    setForm((current) => ({ ...current, [key]: value }));

  const saveBasics = () =>
    save.mutate({
      headline: form.headline,
      bio: form.bio,
      city: form.city,
      state: form.state,
      institution_id: form.institution_id,
      program_name: form.program_name,
      current_year: form.current_year,
      current_semester: form.current_semester,
      cgpa: form.cgpa ? Number(form.cgpa) : undefined,
      graduation_year: form.graduation_year,
      backlogs: form.backlogs,
      target_job_role_id: form.target_job_role_id,
      career_interests: form.career_interests,
      preferred_roles: form.preferred_roles,
      preferred_locations: form.preferred_locations,
      preferred_work_mode: form.preferred_work_mode,
      open_to_relocate: form.open_to_relocate,
      github_url: form.github_url,
      linkedin_url: form.linkedin_url,
    } as Partial<StudentProfile>);

  if (profile.isLoading) {
    return (
      <>
        <PageHeader title="My profile" />
        <SkeletonCard rows={6} />
      </>
    );
  }
  if (profile.error) {
    return (
      <>
        <PageHeader title="My profile" />
        <ErrorState error={profile.error} onRetry={() => void profile.refetch()} />
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="My profile"
        description="Everything here feeds matching. The more complete and honest it is, the better the recommendations."
      />

      {completion.data && (
        <Card className="mb-5 p-5">
          <Progress
            value={completion.data.percentage}
            label="Profile completion"
            showValue
          />
          {completion.data.suggestions.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {completion.data.suggestions.map((suggestion) => (
                <Badge key={suggestion.action} tone="outline" size="md">
                  {suggestion.action} (+{suggestion.impact}%)
                </Badge>
              ))}
            </div>
          )}
        </Card>
      )}

      <Tabs defaultValue="basics">
        <TabsList ariaLabel="Profile sections">
          <TabsTrigger value="basics">Basics</TabsTrigger>
          <TabsTrigger value="preferences">Preferences</TabsTrigger>
          <TabsTrigger value="education">Education</TabsTrigger>
          <TabsTrigger value="experience">Experience</TabsTrigger>
          <TabsTrigger value="projects">Projects</TabsTrigger>
          <TabsTrigger value="achievements">Achievements</TabsTrigger>
        </TabsList>

        <TabsContent value="basics">
          <Card>
            <CardHeader>
              <CardTitle>About you</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                label="Headline"
                placeholder="Final-year CS student · aspiring backend engineer"
                value={form.headline ?? ""}
                onChange={(event) => set("headline", event.target.value)}
              />
              <Textarea
                label="About"
                rows={4}
                placeholder="What you build, what you care about, what you're looking for."
                value={form.bio ?? ""}
                onChange={(event) => set("bio", event.target.value)}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="City"
                  value={form.city ?? ""}
                  onChange={(event) => set("city", event.target.value)}
                />
                <Select
                  label="Institution"
                  value={form.institution_id ?? ""}
                  onChange={(event) => set("institution_id", event.target.value)}
                >
                  <option value="">Select…</option>
                  {institutions.data?.data.map((institution) => (
                    <option key={institution.id} value={institution.id}>
                      {institution.name}
                    </option>
                  ))}
                </Select>
                <Input
                  label="Programme"
                  placeholder="B.Tech Computer Engineering"
                  value={form.program_name ?? ""}
                  onChange={(event) => set("program_name", event.target.value)}
                />
                <Input
                  label="Graduation year"
                  type="number"
                  min={1950}
                  max={2100}
                  value={form.graduation_year ?? ""}
                  onChange={(event) => set("graduation_year", Number(event.target.value))}
                />
                <Input
                  label="CGPA"
                  type="number"
                  step="0.01"
                  min={0}
                  max={10}
                  value={form.cgpa ?? ""}
                  onChange={(event) => set("cgpa", Number(event.target.value))}
                />
                <Input
                  label="Active backlogs"
                  type="number"
                  min={0}
                  value={form.backlogs ?? 0}
                  onChange={(event) => set("backlogs", Number(event.target.value))}
                />
                <Input
                  label="GitHub"
                  placeholder="https://github.com/…"
                  value={form.github_url ?? ""}
                  onChange={(event) => set("github_url", event.target.value)}
                />
                <Input
                  label="LinkedIn"
                  placeholder="https://linkedin.com/in/…"
                  value={form.linkedin_url ?? ""}
                  onChange={(event) => set("linkedin_url", event.target.value)}
                />
              </div>
              <Button isLoading={save.isPending} onClick={saveBasics} leftIcon={<Save />}>
                Save changes
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preferences">
          <Card>
            <CardHeader>
              <CardTitle>What you&rsquo;re looking for</CardTitle>
              <p className="text-sm text-ink-500">
                These feed the career-interest and location factors in matching.
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <Select
                label="Target role"
                hint="Drives your skill-gap analysis and learning path."
                value={form.target_job_role_id ?? ""}
                onChange={(event) => set("target_job_role_id", event.target.value)}
              >
                <option value="">No target role</option>
                {roles.data?.data.map((role) => (
                  <option key={role.id} value={role.id}>
                    {role.title} — {role.family}
                  </option>
                ))}
              </Select>
              <Input
                label="Preferred roles"
                hint="Comma separated, e.g. Backend Developer, Full Stack Developer"
                value={(form.preferred_roles ?? []).join(", ")}
                onChange={(event) =>
                  set(
                    "preferred_roles",
                    event.target.value.split(",").map((v) => v.trim()).filter(Boolean),
                  )
                }
              />
              <Input
                label="Career interests"
                hint="Comma separated, e.g. Backend Development, Cloud"
                value={(form.career_interests ?? []).join(", ")}
                onChange={(event) =>
                  set(
                    "career_interests",
                    event.target.value.split(",").map((v) => v.trim()).filter(Boolean),
                  )
                }
              />
              <Input
                label="Preferred locations"
                hint="Comma separated"
                value={(form.preferred_locations ?? []).join(", ")}
                onChange={(event) =>
                  set(
                    "preferred_locations",
                    event.target.value.split(",").map((v) => v.trim()).filter(Boolean),
                  )
                }
              />
              <Select
                label="Preferred work mode"
                value={form.preferred_work_mode ?? ""}
                onChange={(event) => set("preferred_work_mode", event.target.value)}
              >
                <option value="">No preference</option>
                <option value="ONSITE">On-site</option>
                <option value="HYBRID">Hybrid</option>
                <option value="REMOTE">Remote</option>
              </Select>
              <Button isLoading={save.isPending} onClick={saveBasics} leftIcon={<Save />}>
                Save preferences
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {(["education", "experience", "projects", "achievements"] as SubResource[]).map(
          (resource) => (
            <TabsContent key={resource} value={resource}>
              <SubResourceManager resource={resource} />
            </TabsContent>
          ),
        )}
      </Tabs>
    </>
  );
}
