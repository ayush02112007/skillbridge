"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Save, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Textarea } from "@/components/ui/input";
import { ErrorState, SkeletonCard } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ROLE_LABELS } from "@/lib/constants";
import type { RoleName } from "@/types/api";

interface Company {
  id: string;
  name: string;
  slug: string;
  industry_sector: string;
  website?: string | null;
  description: string;
  about: string;
  headquarters_city?: string | null;
  employee_count?: number | null;
  founded_year?: number | null;
  contact_email?: string | null;
  linkedin_url?: string | null;
  tech_stack: string[];
  benefits: string[];
  verification_status: string;
  is_hiring: boolean;
  open_positions: number;
}

interface TeamMember {
  user_id: string;
  full_name: string;
  email: string;
  designation?: string | null;
  roles: RoleName[];
  is_primary_contact: boolean;
}

export function CompanyProfile() {
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();
  const [form, setForm] = useState<Partial<Company>>({});

  const company = useQuery({
    queryKey: ["company", "me"],
    queryFn: () => api.get<Company>("/companies/me"),
  });

  const team = useQuery({
    queryKey: ["company", "team"],
    queryFn: () => api.get<TeamMember[]>("/companies/me/team"),
  });

  useEffect(() => {
    if (company.data) setForm(company.data);
  }, [company.data]);

  const save = useMutation({
    mutationFn: () =>
      api.patch<Company>("/companies/me", {
        name: form.name,
        industry_sector: form.industry_sector,
        website: form.website,
        description: form.description,
        about: form.about,
        headquarters_city: form.headquarters_city,
        employee_count: form.employee_count ? Number(form.employee_count) : undefined,
        founded_year: form.founded_year ? Number(form.founded_year) : undefined,
        contact_email: form.contact_email,
        linkedin_url: form.linkedin_url,
        tech_stack: form.tech_stack,
        benefits: form.benefits,
        is_hiring: form.is_hiring,
      }),
    onSuccess: () => {
      toast.success("Company profile saved");
      void queryClient.invalidateQueries({ queryKey: ["company"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not save"),
  });

  const canEdit = hasRole("INDUSTRY_ADMIN");

  if (company.isLoading) {
    return (
      <>
        <PageHeader title="Company profile" />
        <SkeletonCard rows={5} />
      </>
    );
  }
  if (company.error) {
    return (
      <>
        <PageHeader title="Company profile" />
        <ErrorState error={company.error} onRetry={() => void company.refetch()} />
      </>
    );
  }

  const set = <K extends keyof Company>(key: K, value: Company[K]) =>
    setForm((current) => ({ ...current, [key]: value }));

  return (
    <>
      <PageHeader
        title="Company profile"
        description="What students see when they look at your postings. A complete profile improves engagement and the interest factor in matching."
        actions={
          canEdit && (
            <Button isLoading={save.isPending} onClick={() => save.mutate()} leftIcon={<Save />}>
              Save changes
            </Button>
          )
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>About the company</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                label="Company name"
                disabled={!canEdit}
                value={form.name ?? ""}
                onChange={(event) => set("name", event.target.value)}
              />
              <Textarea
                label="Short description"
                rows={2}
                disabled={!canEdit}
                hint="One line, shown on posting cards."
                value={form.description ?? ""}
                onChange={(event) => set("description", event.target.value)}
              />
              <Textarea
                label="About"
                rows={5}
                disabled={!canEdit}
                value={form.about ?? ""}
                onChange={(event) => set("about", event.target.value)}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Industry sector"
                  disabled={!canEdit}
                  value={form.industry_sector ?? ""}
                  onChange={(event) => set("industry_sector", event.target.value)}
                />
                <Input
                  label="Headquarters"
                  disabled={!canEdit}
                  value={form.headquarters_city ?? ""}
                  onChange={(event) => set("headquarters_city", event.target.value)}
                />
                <Input
                  label="Employees"
                  type="number"
                  min={0}
                  disabled={!canEdit}
                  value={form.employee_count ?? ""}
                  onChange={(event) => set("employee_count", Number(event.target.value))}
                />
                <Input
                  label="Founded"
                  type="number"
                  disabled={!canEdit}
                  value={form.founded_year ?? ""}
                  onChange={(event) => set("founded_year", Number(event.target.value))}
                />
                <Input
                  label="Website"
                  disabled={!canEdit}
                  value={form.website ?? ""}
                  onChange={(event) => set("website", event.target.value)}
                />
                <Input
                  label="Careers email"
                  type="email"
                  disabled={!canEdit}
                  value={form.contact_email ?? ""}
                  onChange={(event) => set("contact_email", event.target.value)}
                />
              </div>
              <Input
                label="Tech stack"
                hint="Comma separated"
                disabled={!canEdit}
                value={(form.tech_stack ?? []).join(", ")}
                onChange={(event) =>
                  set(
                    "tech_stack",
                    event.target.value.split(",").map((v) => v.trim()).filter(Boolean),
                  )
                }
              />
              <Input
                label="Benefits"
                hint="Comma separated"
                disabled={!canEdit}
                value={(form.benefits ?? []).join(", ")}
                onChange={(event) =>
                  set(
                    "benefits",
                    event.target.value.split(",").map((v) => v.trim()).filter(Boolean),
                  )
                }
              />
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader className="flex-row items-center gap-2.5">
              <span className="flex size-9 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
                <Building2 className="size-4" aria-hidden />
              </span>
              <CardTitle className="flex-1">{company.data?.name}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex flex-wrap gap-1.5">
                <Badge
                  tone={
                    company.data?.verification_status === "VERIFIED" ? "success" : "neutral"
                  }
                >
                  {company.data?.verification_status.toLowerCase()}
                </Badge>
                <Badge tone={company.data?.is_hiring ? "brand" : "neutral"}>
                  {company.data?.is_hiring ? "Hiring" : "Not hiring"}
                </Badge>
              </div>
              <p className="text-sm text-ink-600">
                {company.data?.open_positions} open position
                {company.data?.open_positions === 1 ? "" : "s"}
              </p>
              <p className="text-2xs text-ink-400">
                Public profile: /companies/{company.data?.slug}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center gap-2">
              <Users className="size-4 text-ink-400" aria-hidden />
              <CardTitle>Recruiting team</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="divide-y divide-ink-100">
                {team.data?.map((member) => (
                  <li key={member.user_id} className="flex items-center gap-2.5 py-2.5">
                    <Avatar name={member.full_name} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-ink-900">
                        {member.full_name}
                        {member.is_primary_contact && (
                          <Badge tone="brand" className="ml-1.5">Primary</Badge>
                        )}
                      </p>
                      <p className="truncate text-2xs text-ink-500">
                        {member.designation ?? member.roles.map((r) => ROLE_LABELS[r]).join(", ")}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
