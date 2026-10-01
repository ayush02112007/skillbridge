"use client";

import { useQuery } from "@tanstack/react-query";
import { BadgeCheck, Building2, Compass, Globe, MapPin, Users } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState, SkeletonCard } from "@/components/ui/states";
import { OpportunityCard } from "@/features/shared/opportunity-card";
import { api } from "@/lib/api";
import { APP_NAME } from "@/lib/constants";
import type { Opportunity, Paged } from "@/types/api";

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
  tech_stack: string[];
  benefits: string[];
  verification_status: string;
  is_hiring: boolean;
  open_positions: number;
}

export function PublicCompanyProfile({ slug }: { slug: string }) {
  const company = useQuery({
    queryKey: ["company", slug],
    queryFn: () => api.get<Company>(`/companies/${slug}`),
    retry: false,
  });

  const postings = useQuery({
    queryKey: ["company", slug, "postings"],
    queryFn: () =>
      api.paged<Opportunity>("/opportunities", {
        company_id: company.data?.id,
        page_size: 12,
      }) as Promise<Paged<Opportunity>>,
    enabled: Boolean(company.data?.id),
  });

  if (company.isLoading) {
    return (
      <div className="container max-w-4xl py-10">
        <SkeletonCard rows={5} />
      </div>
    );
  }
  if (company.error || !company.data) {
    return (
      <div className="container max-w-2xl py-16">
        <ErrorState error={company.error} onRetry={() => void company.refetch()} />
      </div>
    );
  }

  const data = company.data;

  return (
    <div className="min-h-dvh bg-surface-muted">
      <header className="border-b border-ink-200 bg-surface">
        <div className="container flex h-14 items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="flex size-7 items-center justify-center rounded-lg bg-brand-700 text-white">
              <Compass className="size-3.5" aria-hidden />
            </span>
            <span className="text-sm font-semibold text-ink-950">{APP_NAME}</span>
          </Link>
          <Link href="/opportunities">
            <Button size="sm" variant="secondary">All opportunities</Button>
          </Link>
        </div>
      </header>

      <main id="main" className="container max-w-4xl py-8">
        <Card className="p-6">
          <div className="flex flex-wrap items-start gap-4">
            <span className="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-brand-50 text-brand-700">
              <Building2 className="size-6" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <h1 className="flex flex-wrap items-center gap-2 text-2xl">
                {data.name}
                {data.verification_status === "VERIFIED" && (
                  <Badge tone="success" size="md">
                    <BadgeCheck className="size-3.5" aria-hidden />
                    Verified
                  </Badge>
                )}
              </h1>
              <p className="mt-1 text-sm text-ink-600">{data.description}</p>
              <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-ink-600">
                <div className="flex items-center gap-1.5">
                  <Building2 className="size-3.5 text-ink-400" aria-hidden />
                  <dd>{data.industry_sector}</dd>
                </div>
                {data.headquarters_city && (
                  <div className="flex items-center gap-1.5">
                    <MapPin className="size-3.5 text-ink-400" aria-hidden />
                    <dd>{data.headquarters_city}</dd>
                  </div>
                )}
                {data.employee_count && (
                  <div className="flex items-center gap-1.5">
                    <Users className="size-3.5 text-ink-400" aria-hidden />
                    <dd>{data.employee_count.toLocaleString()} employees</dd>
                  </div>
                )}
                {data.website && (
                  <div className="flex items-center gap-1.5">
                    <Globe className="size-3.5 text-ink-400" aria-hidden />
                    <dd>
                      <a
                        href={data.website}
                        target="_blank"
                        rel="noreferrer"
                        className="hover:underline"
                      >
                        Website
                      </a>
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          </div>

          {data.about && (
            <p className="mt-5 border-t border-ink-100 pt-5 text-sm leading-relaxed text-ink-700">
              {data.about}
            </p>
          )}

          {(data.tech_stack.length > 0 || data.benefits.length > 0) && (
            <div className="mt-5 grid gap-4 border-t border-ink-100 pt-5 sm:grid-cols-2">
              {data.tech_stack.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
                    Tech stack
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {data.tech_stack.map((item) => (
                      <Badge key={item} tone="neutral">{item}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {data.benefits.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
                    Benefits
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {data.benefits.map((item) => (
                      <Badge key={item} tone="accent">{item}</Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>

        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Open roles ({data.open_positions})</CardTitle>
          </CardHeader>
          <CardContent>
            {postings.isLoading && <SkeletonCard rows={2} />}
            {postings.data?.data.length === 0 && (
              <EmptyState
                className="border-0 bg-transparent"
                title="No open roles right now"
                description="Check back, or explore other companies hiring on SkillBridge."
              />
            )}
            <div className="grid gap-4 md:grid-cols-2">
              {postings.data?.data.map((posting) => (
                <OpportunityCard key={posting.id} opportunity={posting} />
              ))}
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
