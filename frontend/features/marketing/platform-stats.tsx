"use client";

/**
 * Live platform statistics.
 *
 * These are fetched from the public catalogue endpoints rather than hard-coded,
 * so the landing page never shows an invented number. While loading, the tiles
 * show skeletons; if the API is unreachable the section hides itself rather
 * than displaying a fabricated figure.
 */
import { useQuery } from "@tanstack/react-query";
import { Briefcase, Building2, GraduationCap, Sparkles } from "lucide-react";

import { Skeleton } from "@/components/ui/states";
import { api } from "@/lib/api";
import type { Paged } from "@/types/api";

interface Counts {
  skills: number;
  roles: number;
  opportunities: number;
  companies: number;
}

async function fetchCounts(): Promise<Counts> {
  // `meta.total` on a one-item page is the cheapest way to count without
  // adding a bespoke public endpoint.
  const [skills, roles, opportunities, companies] = await Promise.all([
    api.paged<unknown>("/skills", { page_size: 1 }),
    api.paged<unknown>("/job-roles", { page_size: 1 }),
    api.paged<unknown>("/opportunities", { page_size: 1, open_only: true }),
    api.paged<unknown>("/companies", { page_size: 1 }),
  ]);
  const total = (page: Paged<unknown>) => page.meta?.total ?? 0;
  return {
    skills: total(skills),
    roles: total(roles),
    opportunities: total(opportunities),
    companies: total(companies),
  };
}

export function PlatformStats() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["platform-stats"],
    queryFn: fetchCounts,
    staleTime: 5 * 60_000,
    retry: false,
  });

  if (isError) return null;

  const tiles = [
    { key: "skills", label: "Skills tracked", icon: <Sparkles />, value: data?.skills },
    { key: "roles", label: "Career roles mapped", icon: <GraduationCap />, value: data?.roles },
    { key: "opportunities", label: "Open opportunities", icon: <Briefcase />, value: data?.opportunities },
    { key: "companies", label: "Partner companies", icon: <Building2 />, value: data?.companies },
  ];

  return (
    <section
      aria-label="Platform statistics"
      className="border-b border-ink-200/70 bg-surface"
    >
      <div className="container grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-ink-200 bg-ink-200 lg:grid-cols-4 my-10">
        {tiles.map((tile) => (
          <div key={tile.key} className="flex items-center gap-3.5 bg-surface p-5">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700 [&_svg]:size-5">
              {tile.icon}
            </span>
            <div className="min-w-0">
              {isLoading ? (
                <Skeleton className="h-7 w-14" />
              ) : (
                <p className="text-2xl font-semibold tabular-nums leading-none text-ink-950">
                  {tile.value?.toLocaleString() ?? "—"}
                </p>
              )}
              <p className="mt-1 truncate text-xs text-ink-500">{tile.label}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
