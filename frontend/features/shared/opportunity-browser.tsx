"use client";

/**
 * Shared browser for internships, jobs and live projects.
 *
 * One component drives all three listings: the only differences are the
 * endpoint, the copy and which filters are relevant.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Filter, Search, SlidersHorizontal, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { OpportunityCard } from "@/features/shared/opportunity-card";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Opportunity, Paged, SkillBrief } from "@/types/api";

export interface BrowserConfig {
  endpoint: "/internships" | "/jobs" | "/projects" | "/opportunities";
  emptyTitle: string;
  emptyDescription: string;
  showStipend?: boolean;
}

export function OpportunityBrowser({ config }: { config: BrowserConfig }) {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [location, setLocation] = useState("");
  const [workMode, setWorkMode] = useState("");
  const [skillId, setSkillId] = useState("");
  const [sortBy, setSortBy] = useState("match");
  const [page, setPage] = useState(1);
  const [showFilters, setShowFilters] = useState(false);

  const filters = {
    q: search || undefined,
    location: location || undefined,
    work_mode: workMode || undefined,
    skill_id: skillId || undefined,
    sort_by: sortBy,
    page,
    page_size: 12,
  };

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: [config.endpoint, filters],
    queryFn: () => api.paged<Opportunity>(config.endpoint, filters) as Promise<Paged<Opportunity>>,
  });

  const { data: skills } = useQuery({
    queryKey: ["skills", "filter"],
    queryFn: () =>
      api.paged<SkillBrief>("/skills", { page_size: 40, sort_by: "demand_score" }),
    staleTime: 10 * 60_000,
  });

  const toggleSave = useMutation({
    mutationFn: async (opportunity: Opportunity) => {
      if (opportunity.is_saved) {
        await api.delete(`/opportunities/${opportunity.id}/save`);
        return false;
      }
      await api.post(`/opportunities/${opportunity.id}/save`);
      return true;
    },
    onSuccess: (saved) => {
      toast.success(saved ? "Saved" : "Removed from saved");
      void queryClient.invalidateQueries({ queryKey: [config.endpoint] });
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.message : "Could not update"),
  });

  const activeFilters = [location, workMode, skillId].filter(Boolean).length;

  const applySearch = (event: React.FormEvent) => {
    event.preventDefault();
    setSearch(query);
    setPage(1);
  };

  const clearFilters = () => {
    setLocation("");
    setWorkMode("");
    setSkillId("");
    setPage(1);
  };

  return (
    <>
      <Card className="mb-5 p-4">
        <form onSubmit={applySearch} className="flex flex-wrap items-end gap-3">
          <div className="min-w-[14rem] flex-1">
            <Input
              label="Search"
              placeholder="Role, company or skill"
              leftIcon={<Search />}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <Select
            label="Sort by"
            value={sortBy}
            onChange={(event) => {
              setSortBy(event.target.value);
              setPage(1);
            }}
            className="w-40"
          >
            <option value="match">Best match</option>
            <option value="recent">Most recent</option>
            <option value="deadline">Closing soonest</option>
            <option value="applications">Most applied</option>
          </Select>
          <Button type="submit">Search</Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => setShowFilters((value) => !value)}
            leftIcon={<SlidersHorizontal />}
            aria-expanded={showFilters}
          >
            Filters
            {activeFilters > 0 && (
              <span className="ml-1 rounded-full bg-brand-700 px-1.5 text-2xs text-white">
                {activeFilters}
              </span>
            )}
          </Button>
        </form>

        {showFilters && (
          <div className="mt-4 grid gap-3 border-t border-ink-100 pt-4 sm:grid-cols-3">
            <Input
              label="Location"
              placeholder="e.g. Bengaluru"
              value={location}
              onChange={(event) => {
                setLocation(event.target.value);
                setPage(1);
              }}
            />
            <Select
              label="Work mode"
              value={workMode}
              onChange={(event) => {
                setWorkMode(event.target.value);
                setPage(1);
              }}
            >
              <option value="">Any</option>
              <option value="ONSITE">On-site</option>
              <option value="REMOTE">Remote</option>
              <option value="HYBRID">Hybrid</option>
            </Select>
            <Select
              label="Requires skill"
              value={skillId}
              onChange={(event) => {
                setSkillId(event.target.value);
                setPage(1);
              }}
            >
              <option value="">Any skill</option>
              {skills?.data.map((skill) => (
                <option key={skill.id} value={skill.id}>{skill.name}</option>
              ))}
            </Select>
            {activeFilters > 0 && (
              <div className="sm:col-span-3">
                <Button variant="ghost" size="sm" onClick={clearFilters} leftIcon={<X />}>
                  Clear filters
                </Button>
              </div>
            )}
          </div>
        )}
      </Card>

      {isLoading && <SkeletonList count={6} rows={4} />}
      {error && <ErrorState error={error} onRetry={() => void refetch()} />}

      {data && data.data.length === 0 && (
        <EmptyState
          icon={<Filter />}
          title={search || activeFilters ? "No results match those filters" : config.emptyTitle}
          description={
            search || activeFilters
              ? "Try widening the search — fewer filters, or a broader skill."
              : config.emptyDescription
          }
          action={
            (search || activeFilters) && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setQuery("");
                  setSearch("");
                  clearFilters();
                }}
              >
                Clear everything
              </Button>
            )
          }
        />
      )}

      {data && data.data.length > 0 && (
        <>
          <p className="mb-3 text-sm text-ink-500">
            {data.meta.total} result{data.meta.total === 1 ? "" : "s"}
            {sortBy === "match" && " · ranked by your skill fit"}
          </p>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.data.map((opportunity) => (
              <OpportunityCard
                key={opportunity.id}
                opportunity={opportunity}
                onToggleSave={(item) => toggleSave.mutate(item)}
              />
            ))}
          </div>

          {data.meta.total_pages > 1 && (
            <nav
              className="mt-6 flex items-center justify-center gap-2"
              aria-label="Pagination"
            >
              <Button
                variant="secondary"
                size="sm"
                disabled={!data.meta.has_previous}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="px-2 text-sm text-ink-600">
                Page {data.meta.page} of {data.meta.total_pages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={!data.meta.has_next}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </nav>
          )}
        </>
      )}
    </>
  );
}
