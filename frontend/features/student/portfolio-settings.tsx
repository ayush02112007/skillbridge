"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Download, ExternalLink, Eye, FileText, Globe, Lock, Plus, Save, Users,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox, Input, Select, Textarea } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState, ErrorState, SkeletonCard } from "@/components/ui/states";
import { api, ApiError, downloadFile } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import type { Visibility } from "@/types/api";

interface Portfolio {
  id: string;
  slug: string;
  headline: string;
  about: string;
  theme: string;
  visibility: Visibility;
  sections: string[];
  contact_email_visible: boolean;
  phone_visible: boolean;
  view_count: number;
  completion_percentage: number;
  published_at?: string | null;
}

interface Resume {
  id: string;
  title: string;
  template: string;
  content: Record<string, unknown>;
  is_default: boolean;
  last_exported_at?: string | null;
  updated_at: string;
}

const VISIBILITY_OPTIONS: {
  value: Visibility;
  label: string;
  description: string;
  icon: React.ReactNode;
}[] = [
  {
    value: "PUBLIC",
    label: "Public",
    description: "Anyone with the link can view it, including search engines.",
    icon: <Globe />,
  },
  {
    value: "INSTITUTION_ONLY",
    label: "Institution only",
    description:
      "Your institution's staff, and companies you have applied to.",
    icon: <Users />,
  },
  {
    value: "PRIVATE",
    label: "Private",
    description: "Only you. The public link returns a 404.",
    icon: <Lock />,
  },
];

export function PortfolioSettings() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<Partial<Portfolio>>({});
  const [resumeTitle, setResumeTitle] = useState("My Resume");
  const [template, setTemplate] = useState("modern");

  const portfolio = useQuery({
    queryKey: ["portfolio", "me"],
    queryFn: () => api.get<Portfolio>("/portfolio/me"),
  });

  const resumes = useQuery({
    queryKey: ["resumes"],
    queryFn: () => api.get<Resume[]>("/resumes"),
  });

  useEffect(() => {
    if (portfolio.data) setForm(portfolio.data);
  }, [portfolio.data]);

  const save = useMutation({
    mutationFn: (payload: Partial<Portfolio>) =>
      api.patch<Portfolio>("/portfolio/me", payload),
    onSuccess: () => {
      toast.success("Portfolio updated");
      void queryClient.invalidateQueries({ queryKey: ["portfolio"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not save"),
  });

  const createResume = useMutation({
    mutationFn: async () => {
      // Pre-fill from the profile so the builder never starts empty, and never
      // invents content the student did not enter.
      const content = await api.get<Record<string, unknown>>("/resumes/prefill");
      return api.post<Resume>("/resumes", {
        title: resumeTitle,
        template,
        content,
        is_default: (resumes.data?.length ?? 0) === 0,
      });
    },
    onSuccess: () => {
      toast.success("Resume created from your profile");
      void queryClient.invalidateQueries({ queryKey: ["resumes"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not create resume"),
  });

  const exportResume = async (resume: Resume) => {
    try {
      await downloadFile(
        `/resumes/${resume.id}/export`,
        `${resume.title.replace(/\s+/g, "-").toLowerCase()}.pdf`,
      );
      toast.success("Resume downloaded");
      void queryClient.invalidateQueries({ queryKey: ["resumes"] });
    } catch {
      toast.error("Could not export the resume");
    }
  };

  if (portfolio.isLoading) {
    return (
      <>
        <PageHeader title="Digital portfolio" />
        <SkeletonCard rows={5} />
      </>
    );
  }
  if (portfolio.error) {
    return (
      <>
        <PageHeader title="Digital portfolio" />
        <ErrorState error={portfolio.error} onRetry={() => void portfolio.refetch()} />
      </>
    );
  }

  const publicUrl = form.slug ? `/portfolio/${form.slug}` : null;

  return (
    <>
      <PageHeader
        title="Digital portfolio"
        description="One link that shows what you can actually do, with verified credentials marked as such."
        actions={
          publicUrl && (
            <Link href={publicUrl} target="_blank">
              <Button leftIcon={<ExternalLink />}>View public portfolio</Button>
            </Link>
          )
        }
      />

      <Tabs defaultValue="portfolio">
        <TabsList ariaLabel="Portfolio sections">
          <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
          <TabsTrigger value="resume">Resume builder</TabsTrigger>
        </TabsList>

        <TabsContent value="portfolio">
          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Presentation</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input
                  label="Public link"
                  value={publicUrl ?? ""}
                  readOnly
                  hint="Share this link on applications and your CV."
                />
                <Input
                  label="Headline"
                  placeholder="Final-year CS student · aspiring backend engineer"
                  value={form.headline ?? ""}
                  onChange={(event) =>
                    setForm((c) => ({ ...c, headline: event.target.value }))
                  }
                />
                <Textarea
                  label="About"
                  rows={4}
                  value={form.about ?? ""}
                  onChange={(event) => setForm((c) => ({ ...c, about: event.target.value }))}
                />
                <Select
                  label="Theme"
                  value={form.theme ?? "slate"}
                  onChange={(event) => setForm((c) => ({ ...c, theme: event.target.value }))}
                >
                  {["slate", "indigo", "emerald", "amber", "rose"].map((theme) => (
                    <option key={theme} value={theme}>{theme}</option>
                  ))}
                </Select>

                <div className="space-y-2 border-t border-ink-100 pt-4">
                  <p className="text-sm font-medium text-ink-800">Contact details</p>
                  <Checkbox
                    label="Show my email address"
                    description="Only enable this if you are happy for it to be public."
                    checked={form.contact_email_visible ?? false}
                    onChange={(event) =>
                      setForm((c) => ({ ...c, contact_email_visible: event.target.checked }))
                    }
                  />
                  <Checkbox
                    label="Show my phone number"
                    checked={form.phone_visible ?? false}
                    onChange={(event) =>
                      setForm((c) => ({ ...c, phone_visible: event.target.checked }))
                    }
                  />
                </div>

                <Button
                  isLoading={save.isPending}
                  onClick={() =>
                    save.mutate({
                      headline: form.headline,
                      about: form.about,
                      theme: form.theme,
                      contact_email_visible: form.contact_email_visible,
                      phone_visible: form.phone_visible,
                    })
                  }
                  leftIcon={<Save />}
                >
                  Save
                </Button>
              </CardContent>
            </Card>

            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Who can see it</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {VISIBILITY_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => {
                        setForm((c) => ({ ...c, visibility: option.value }));
                        save.mutate({ visibility: option.value });
                      }}
                      className={cn(
                        "flex w-full items-start gap-3 rounded-xl border p-3 text-left transition-colors",
                        form.visibility === option.value
                          ? "border-brand-600 bg-brand-50/60 ring-1 ring-brand-600"
                          : "border-ink-200 hover:border-ink-300 hover:bg-ink-50",
                      )}
                    >
                      <span
                        className={cn(
                          "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg [&_svg]:size-4",
                          form.visibility === option.value
                            ? "bg-brand-700 text-white"
                            : "bg-ink-100 text-ink-500",
                        )}
                        aria-hidden
                      >
                        {option.icon}
                      </span>
                      <span className="min-w-0">
                        <span className="block text-sm font-medium text-ink-900">
                          {option.label}
                        </span>
                        <span className="block text-xs text-ink-500">
                          {option.description}
                        </span>
                      </span>
                    </button>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Portfolio health</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Progress
                    value={form.completion_percentage ?? 0}
                    label="Completeness"
                    showValue
                  />
                  <dl className="space-y-1.5 text-sm">
                    <div className="flex items-center justify-between">
                      <dt className="text-ink-500">Views</dt>
                      <dd className="flex items-center gap-1 font-medium tabular-nums text-ink-800">
                        <Eye className="size-3.5 text-ink-400" aria-hidden />
                        {form.view_count ?? 0}
                      </dd>
                    </div>
                    <div className="flex items-center justify-between">
                      <dt className="text-ink-500">Published</dt>
                      <dd className="font-medium text-ink-800">
                        {form.published_at ? formatDate(form.published_at) : "Not yet"}
                      </dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="resume">
          <Card className="mb-4 p-5">
            <p className="text-sm text-ink-600">
              Resumes are built from data already on your profile — nothing is
              invented to fill space. Export as PDF in one of four templates.
            </p>
            <div className="mt-4 flex flex-wrap items-end gap-3">
              <Input
                label="Resume name"
                value={resumeTitle}
                onChange={(event) => setResumeTitle(event.target.value)}
                className="w-56"
              />
              <Select
                label="Template"
                value={template}
                onChange={(event) => setTemplate(event.target.value)}
                className="w-44"
              >
                <option value="modern">Modern</option>
                <option value="minimal">Minimal</option>
                <option value="professional">Professional</option>
                <option value="technical">Technical</option>
              </Select>
              <Button
                isLoading={createResume.isPending}
                onClick={() => createResume.mutate()}
                leftIcon={<Plus />}
              >
                Build from my profile
              </Button>
            </div>
          </Card>

          {resumes.isLoading && <SkeletonCard rows={2} />}
          {resumes.data?.length === 0 && (
            <EmptyState
              icon={<FileText />}
              title="No resumes yet"
              description="Build one from your profile — it takes a second and stays in sync with what you have entered."
            />
          )}

          <div className="space-y-3">
            {resumes.data?.map((resume) => (
              <Card key={resume.id} className="flex flex-wrap items-center gap-3 p-4">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-ink-100 text-ink-500">
                  <FileText className="size-4" aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink-900">
                    {resume.title}
                    {resume.is_default && <Badge tone="brand">Default</Badge>}
                    <Badge tone="outline">{resume.template}</Badge>
                  </p>
                  <p className="text-xs text-ink-500">
                    Updated {formatDate(resume.updated_at)}
                    {resume.last_exported_at
                      ? ` · last exported ${formatDate(resume.last_exported_at)}`
                      : ""}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="secondary"
                  leftIcon={<Download />}
                  onClick={() => void exportResume(resume)}
                >
                  Export PDF
                </Button>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </>
  );
}
