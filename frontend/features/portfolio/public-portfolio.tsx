"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Award, BadgeCheck, Briefcase, Compass, ExternalLink, Github, GraduationCap,
  Linkedin, Mail, MapPin, Phone, Sparkles, Trophy,
} from "lucide-react";
import Link from "next/link";

import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { SkillBadge } from "@/components/ui/skill-badge";
import { EmptyState, ErrorState, SkeletonCard } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { APP_NAME } from "@/lib/constants";
import { cn, formatDate } from "@/lib/utils";
import type { ProficiencyLevel, PublicPortfolio, SkillSource } from "@/types/api";

function Section({
  title,
  icon,
  children,
  count,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  count?: number;
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-center gap-2.5">
        <span className="flex size-8 items-center justify-center rounded-lg bg-brand-50 text-brand-700 [&_svg]:size-4">
          {icon}
        </span>
        <CardTitle className="flex-1">{title}</CardTitle>
        {count !== undefined && <Badge tone="neutral">{count}</Badge>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export function PublicPortfolioView({ slug }: { slug: string }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["portfolio", slug],
    queryFn: () => api.get<PublicPortfolio>(`/portfolio/${slug}`),
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="container max-w-4xl py-10">
        <SkeletonCard rows={6} />
      </div>
    );
  }

  if (error) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <div className="container max-w-2xl py-16">
        {notFound ? (
          <EmptyState
            icon={<Compass />}
            title="This portfolio is not available"
            description="It may be private, restricted to the student's institution, or the link may be out of date."
            action={
              <Link href="/">
                <Button variant="secondary">Back to SkillBridge</Button>
              </Link>
            }
          />
        ) : (
          <ErrorState error={error} onRetry={() => void refetch()} />
        )}
      </div>
    );
  }

  if (!data) return null;

  const skillsByCategory = data.skills.reduce<Record<string, typeof data.skills>>(
    (acc, skill) => {
      (acc[skill.category || "Other"] ??= []).push(skill);
      return acc;
    },
    {},
  );

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
          <Link href="/register">
            <Button size="sm" variant="secondary">Create your own</Button>
          </Link>
        </div>
      </header>

      <main id="main" className="container max-w-4xl py-8">
        {/* Identity */}
        <Card className="overflow-hidden">
          <div className="h-20 bg-gradient-to-r from-brand-800 to-brand-600" aria-hidden />
          <div className="px-6 pb-6">
            <div className="-mt-10 flex flex-wrap items-end justify-between gap-4">
              <div className="flex items-end gap-4">
                <Avatar
                  name={data.full_name}
                  src={data.avatar_url}
                  size="xl"
                  className="ring-4 ring-white"
                />
                <div className="mb-1 min-w-0">
                  <h1 className="text-2xl">{data.full_name}</h1>
                  {data.headline && (
                    <p className="mt-0.5 text-sm text-ink-600">{data.headline}</p>
                  )}
                </div>
              </div>

              {data.verified_credential_count > 0 && (
                <Badge tone="success" size="md" className="mb-2">
                  <BadgeCheck className="size-3.5" aria-hidden />
                  {data.verified_credential_count} verified credential
                  {data.verified_credential_count === 1 ? "" : "s"}
                </Badge>
              )}
            </div>

            <dl className="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-sm text-ink-600">
              {data.institution_name && (
                <div className="flex items-center gap-1.5">
                  <GraduationCap className="size-4 text-ink-400" aria-hidden />
                  <dd>
                    {data.program_name ? `${data.program_name}, ` : ""}
                    {data.institution_name}
                    {data.graduation_year ? ` (${data.graduation_year})` : ""}
                  </dd>
                </div>
              )}
              {data.city && (
                <div className="flex items-center gap-1.5">
                  <MapPin className="size-4 text-ink-400" aria-hidden />
                  <dd>{data.city}</dd>
                </div>
              )}
              {data.email && (
                <div className="flex items-center gap-1.5">
                  <Mail className="size-4 text-ink-400" aria-hidden />
                  <dd>
                    <a href={`mailto:${data.email}`} className="hover:underline">
                      {data.email}
                    </a>
                  </dd>
                </div>
              )}
              {data.phone && (
                <div className="flex items-center gap-1.5">
                  <Phone className="size-4 text-ink-400" aria-hidden />
                  <dd>{data.phone}</dd>
                </div>
              )}
            </dl>

            <div className="mt-4 flex flex-wrap gap-2">
              {data.github_url && (
                <a href={data.github_url} target="_blank" rel="noreferrer">
                  <Button size="sm" variant="secondary" leftIcon={<Github />}>GitHub</Button>
                </a>
              )}
              {data.linkedin_url && (
                <a href={data.linkedin_url} target="_blank" rel="noreferrer">
                  <Button size="sm" variant="secondary" leftIcon={<Linkedin />}>LinkedIn</Button>
                </a>
              )}
            </div>

            {data.about && (
              <p className="mt-5 border-t border-ink-100 pt-5 text-sm leading-relaxed text-ink-700">
                {data.about}
              </p>
            )}

            {data.badges.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-1.5">
                {data.badges.map((badge) => (
                  <Badge key={badge.code} tone="accent" size="md">
                    <Award className="size-3" aria-hidden />
                    {badge.name}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </Card>

        <div className="mt-6 space-y-6">
          {data.skills.length > 0 && (
            <Section title="Skills" icon={<Sparkles />} count={data.skills.length}>
              <div className="space-y-4">
                {Object.entries(skillsByCategory).map(([category, skills]) => (
                  <div key={category}>
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
                      {category}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {skills.map((skill) => (
                        <SkillBadge
                          key={skill.name}
                          name={skill.name}
                          level={skill.level as ProficiencyLevel}
                          source={skill.source as SkillSource}
                          isVerified={skill.is_verified}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {data.experience.length > 0 && (
            <Section title="Experience" icon={<Briefcase />} count={data.experience.length}>
              <ol className="space-y-4">
                {data.experience.map((entry, index) => (
                  <li key={index} className="border-l-2 border-ink-200 pl-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-ink-900">
                        {String(entry.title)}
                      </p>
                      {Boolean(entry.is_verified) && (
                        <Badge tone="success">
                          <BadgeCheck className="size-3" aria-hidden />
                          Verified
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-ink-600">{String(entry.organization)}</p>
                    <p className="text-xs text-ink-500">
                      {formatDate(entry.start_date as string)} –{" "}
                      {entry.is_current ? "Present" : formatDate(entry.end_date as string)}
                      {entry.location ? ` · ${entry.location}` : ""}
                    </p>
                    {Boolean(entry.description) && (
                      <p className="mt-1.5 text-sm leading-relaxed text-ink-700">
                        {String(entry.description)}
                      </p>
                    )}
                    {Array.isArray(entry.skill_tags) && entry.skill_tags.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {(entry.skill_tags as string[]).map((tag) => (
                          <Badge key={tag} tone="neutral">{tag}</Badge>
                        ))}
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            </Section>
          )}

          {data.projects.length > 0 && (
            <Section title="Projects" icon={<Trophy />} count={data.projects.length}>
              <div className="grid gap-4 sm:grid-cols-2">
                {data.projects.map((project, index) => (
                  <div key={index} className="rounded-xl border border-ink-200 p-4">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-semibold text-ink-900">
                        {String(project.title)}
                      </p>
                      {Boolean(project.is_featured) && <Badge tone="accent">Featured</Badge>}
                    </div>
                    {Boolean(project.description) && (
                      <p className="mt-1.5 text-sm leading-relaxed text-ink-600">
                        {String(project.description)}
                      </p>
                    )}
                    {Array.isArray(project.skill_tags) && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {(project.skill_tags as string[]).map((tag) => (
                          <Badge key={tag} tone="neutral">{tag}</Badge>
                        ))}
                      </div>
                    )}
                    {Boolean(project.repository_url) && (
                      <a
                        href={String(project.repository_url)}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-2.5 inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:underline"
                      >
                        View code
                        <ExternalLink className="size-3" aria-hidden />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {data.education.length > 0 && (
            <Section title="Education" icon={<GraduationCap />} count={data.education.length}>
              <ul className="space-y-3">
                {data.education.map((entry, index) => (
                  <li key={index} className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink-900">
                        {String(entry.program ?? entry.level)}
                        {Boolean(entry.is_verified) && (
                          <Badge tone="success">
                            <BadgeCheck className="size-3" aria-hidden />
                            Verified
                          </Badge>
                        )}
                      </p>
                      <p className="text-sm text-ink-600">{String(entry.institution_name)}</p>
                    </div>
                    <div className="text-right text-xs text-ink-500">
                      <p>
                        {String(entry.start_year ?? "")} – {String(entry.end_year ?? "")}
                      </p>
                      {entry.score_value ? (
                        <p className="font-medium text-ink-700">
                          {String(entry.score_type) === "CGPA"
                            ? `CGPA ${entry.score_value}`
                            : `${entry.score_value}%`}
                        </p>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {data.certifications.length > 0 && (
            <Section title="Certifications" icon={<Award />} count={data.certifications.length}>
              <ul className="space-y-2.5">
                {data.certifications.map((entry, index) => (
                  <li key={index} className="flex flex-wrap items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink-900">
                        {String(entry.name)}
                        {Boolean(entry.is_verified) && (
                          <Badge tone="success">
                            <BadgeCheck className="size-3" aria-hidden />
                            Verified
                          </Badge>
                        )}
                      </p>
                      <p className="text-xs text-ink-500">{String(entry.issuer)}</p>
                    </div>
                    <span className="text-xs text-ink-500">
                      {formatDate(entry.issued_on as string)}
                    </span>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {data.achievements.length > 0 && (
            <Section title="Achievements" icon={<Trophy />} count={data.achievements.length}>
              <ul className="space-y-2.5">
                {data.achievements.map((entry, index) => (
                  <li key={index}>
                    <p className="text-sm font-medium text-ink-900">
                      {String(entry.title)}
                      {entry.position ? (
                        <Badge tone="accent" className="ml-2">
                          {String(entry.position)}
                        </Badge>
                      ) : null}
                    </p>
                    <p className="text-xs text-ink-500">
                      {String(entry.issuer ?? "")}
                      {entry.achieved_on ? ` · ${formatDate(entry.achieved_on as string)}` : ""}
                    </p>
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>

        <p className="mt-8 text-center text-xs text-ink-400">
          Built with {APP_NAME}. Verified badges indicate credentials confirmed
          by the student&rsquo;s institution or a hiring company.
        </p>
      </main>
    </div>
  );
}
