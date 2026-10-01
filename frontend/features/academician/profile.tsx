"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox, Input, Select, Textarea } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { ErrorState, SkeletonCard } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import type { Institution, Paged } from "@/types/api";

interface AcademicianProfile {
  id: string;
  full_name: string;
  email?: string | null;
  institution_id?: string | null;
  institution_name?: string | null;
  designation?: string | null;
  employee_code?: string | null;
  highest_qualification?: string | null;
  specialization?: string | null;
  teaching_experience_years: number;
  industry_experience_years: number;
  research_areas: string[];
  expertise_areas: string[];
  publications_count: number;
  patents_count: number;
  orcid_id?: string | null;
  google_scholar_url?: string | null;
  bio: string;
  city?: string | null;
  is_available_for_mentorship: boolean;
  is_available_for_consultancy: boolean;
  profile_completion: number;
}

export function AcademicianProfileEditor() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<Partial<AcademicianProfile>>({});

  const profile = useQuery({
    queryKey: ["academician", "profile"],
    queryFn: () => api.get<AcademicianProfile>("/academicians/me"),
  });

  const institutions = useQuery({
    queryKey: ["institutions", "list"],
    queryFn: () =>
      api.paged<Institution>("/institutions", { page_size: 60 }) as Promise<Paged<Institution>>,
    staleTime: 10 * 60_000,
  });

  useEffect(() => {
    if (profile.data) setForm(profile.data);
  }, [profile.data]);

  const save = useMutation({
    mutationFn: () =>
      api.patch<AcademicianProfile>("/academicians/me", {
        institution_id: form.institution_id || undefined,
        designation: form.designation,
        employee_code: form.employee_code,
        highest_qualification: form.highest_qualification,
        specialization: form.specialization,
        teaching_experience_years: Number(form.teaching_experience_years ?? 0),
        industry_experience_years: Number(form.industry_experience_years ?? 0),
        research_areas: form.research_areas,
        expertise_areas: form.expertise_areas,
        publications_count: Number(form.publications_count ?? 0),
        patents_count: Number(form.patents_count ?? 0),
        orcid_id: form.orcid_id,
        google_scholar_url: form.google_scholar_url,
        bio: form.bio,
        city: form.city,
        is_available_for_mentorship: form.is_available_for_mentorship,
        is_available_for_consultancy: form.is_available_for_consultancy,
      }),
    onSuccess: () => {
      toast.success("Profile saved");
      void queryClient.invalidateQueries({ queryKey: ["academician"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not save"),
  });

  const set = <K extends keyof AcademicianProfile>(
    key: K,
    value: AcademicianProfile[K],
  ) => setForm((current) => ({ ...current, [key]: value }));

  if (profile.isLoading) {
    return (
      <>
        <PageHeader title="My profile" />
        <SkeletonCard rows={5} />
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
        description="Your expertise determines which industry programmes and research calls we surface to you."
      />

      <Card className="mb-5 p-5">
        <Progress
          value={form.profile_completion ?? 0}
          label="Profile completion"
          showValue
        />
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Academic details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
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
              label="Designation"
              placeholder="Associate Professor"
              value={form.designation ?? ""}
              onChange={(event) => set("designation", event.target.value)}
            />
            <Input
              label="Highest qualification"
              placeholder="Ph.D."
              value={form.highest_qualification ?? ""}
              onChange={(event) => set("highest_qualification", event.target.value)}
            />
            <Input
              label="Specialisation"
              placeholder="Distributed Systems"
              value={form.specialization ?? ""}
              onChange={(event) => set("specialization", event.target.value)}
            />
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Teaching experience (years)"
                type="number"
                min={0}
                value={form.teaching_experience_years ?? 0}
                onChange={(event) =>
                  set("teaching_experience_years", Number(event.target.value))
                }
              />
              <Input
                label="Industry experience (years)"
                type="number"
                min={0}
                value={form.industry_experience_years ?? 0}
                onChange={(event) =>
                  set("industry_experience_years", Number(event.target.value))
                }
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Research & availability</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              label="Bio"
              rows={4}
              value={form.bio ?? ""}
              onChange={(event) => set("bio", event.target.value)}
            />
            <Input
              label="Research areas"
              hint="Comma separated — these are matched against industry research calls."
              value={(form.research_areas ?? []).join(", ")}
              onChange={(event) =>
                set(
                  "research_areas",
                  event.target.value.split(",").map((v) => v.trim()).filter(Boolean),
                )
              }
            />
            <Input
              label="Expertise areas"
              hint="Comma separated — matched against faculty programmes."
              value={(form.expertise_areas ?? []).join(", ")}
              onChange={(event) =>
                set(
                  "expertise_areas",
                  event.target.value.split(",").map((v) => v.trim()).filter(Boolean),
                )
              }
            />
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Publications"
                type="number"
                min={0}
                value={form.publications_count ?? 0}
                onChange={(event) => set("publications_count", Number(event.target.value))}
              />
              <Input
                label="Patents"
                type="number"
                min={0}
                value={form.patents_count ?? 0}
                onChange={(event) => set("patents_count", Number(event.target.value))}
              />
            </div>
            <Input
              label="Google Scholar"
              placeholder="https://scholar.google.com/…"
              value={form.google_scholar_url ?? ""}
              onChange={(event) => set("google_scholar_url", event.target.value)}
            />
            <div className="space-y-2 border-t border-ink-100 pt-4">
              <Checkbox
                label="Available for student mentorship"
                checked={form.is_available_for_mentorship ?? false}
                onChange={(event) =>
                  set("is_available_for_mentorship", event.target.checked)
                }
              />
              <Checkbox
                label="Available for industry consultancy"
                checked={form.is_available_for_consultancy ?? false}
                onChange={(event) =>
                  set("is_available_for_consultancy", event.target.checked)
                }
              />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-5">
        <Button isLoading={save.isPending} onClick={() => save.mutate()} leftIcon={<Save />}>
          Save profile
        </Button>
      </div>
    </>
  );
}
