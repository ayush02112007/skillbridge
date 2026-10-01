"use client";

/**
 * Global command palette (Cmd/Ctrl-K, or "/" when not typing).
 * Searches every entity through the backend's single search endpoint.
 */
import { useQuery } from "@tanstack/react-query";
import {
  Briefcase, Building2, Calendar, FlaskConical, GraduationCap, Search,
  Sparkles, Target, Users,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { GlobalSearch, SearchHit } from "@/types/api";

const ICONS: Record<string, React.ReactNode> = {
  opportunity: <Briefcase />, internship: <GraduationCap />, job: <Briefcase />,
  live_project: <FlaskConical />, program: <GraduationCap />,
  company: <Building2 />, skill: <Sparkles />, job_role: <Target />,
  mentor: <Users />, event: <Calendar />, research: <FlaskConical />,
};

function useDebounced<T>(value: T, delay = 220): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const debounced = useDebounced(query);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const { data, isFetching } = useQuery({
    queryKey: ["search", debounced],
    queryFn: () =>
      api.get<GlobalSearch>("/search", { q: debounced, limit_per_group: 4 }),
    enabled: open && debounced.trim().length > 0,
    staleTime: 30_000,
  });

  const flat: SearchHit[] = useMemo(
    () => data?.groups.flatMap((group) => group.results) ?? [],
    [data],
  );

  useEffect(() => setCursor(0), [debounced]);

  useEffect(() => {
    if (open) {
      setQuery("");
      window.setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onOpenChange(false);
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setCursor((c) => Math.min(c + 1, Math.max(0, flat.length - 1)));
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setCursor((c) => Math.max(0, c - 1));
      }
      if (event.key === "Enter" && flat[cursor]) {
        event.preventDefault();
        router.push(flat[cursor].url);
        onOpenChange(false);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, flat, cursor, router, onOpenChange]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[12vh]">
      <div
        className="absolute inset-0 animate-fade-in bg-canvas/60 backdrop-blur-[2px]"
        onClick={() => onOpenChange(false)}
        aria-hidden
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Search SkillBridge"
        className="relative z-10 w-full max-w-xl animate-slide-up overflow-hidden rounded-2xl bg-surface shadow-popover"
      >
        <div className="flex items-center gap-3 border-b border-ink-100 px-4">
          <Search className="size-4 shrink-0 text-ink-400" aria-hidden />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search opportunities, skills, companies, mentors…"
            aria-label="Search"
            className="h-12 w-full bg-transparent text-sm text-ink-900 placeholder:text-ink-400 focus:outline-none"
          />
          <kbd className="hidden shrink-0 rounded border border-ink-200 bg-ink-50 px-1.5 py-0.5 font-mono text-2xs text-ink-500 sm:block">
            esc
          </kbd>
        </div>

        <div className="max-h-[52vh] overflow-y-auto p-2">
          {!debounced.trim() && (
            <p className="px-3 py-8 text-center text-sm text-ink-400">
              Start typing to search across the whole platform.
            </p>
          )}
          {debounced.trim() && isFetching && (
            <p className="px-3 py-8 text-center text-sm text-ink-400">Searching…</p>
          )}
          {debounced.trim() && !isFetching && flat.length === 0 && (
            <p className="px-3 py-8 text-center text-sm text-ink-400">
              No matches for &ldquo;{debounced}&rdquo;.
            </p>
          )}

          {data?.groups.map((group) => (
            <div key={group.type} className="mb-1">
              <p className="px-3 py-1.5 text-2xs font-semibold uppercase tracking-wide text-ink-400">
                {group.label}
                {group.total > group.results.length && (
                  <span className="ml-1 font-normal text-ink-300">
                    ({group.total})
                  </span>
                )}
              </p>
              {group.results.map((hit) => {
                const index = flat.findIndex((h) => h.id === hit.id && h.url === hit.url);
                return (
                  <button
                    key={`${hit.type}-${hit.id}`}
                    type="button"
                    onMouseEnter={() => setCursor(index)}
                    onClick={() => {
                      router.push(hit.url);
                      onOpenChange(false);
                    }}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors",
                      index === cursor ? "bg-brand-50" : "hover:bg-ink-50",
                    )}
                  >
                    <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-ink-100 text-ink-500 [&_svg]:size-3.5">
                      {ICONS[hit.type] ?? <Search />}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-ink-900">
                        {hit.title}
                      </span>
                      {hit.subtitle && (
                        <span className="block truncate text-xs text-ink-500">
                          {hit.subtitle}
                        </span>
                      )}
                    </span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        <div className="flex items-center gap-4 border-t border-ink-100 bg-surface-muted px-4 py-2 text-2xs text-ink-400">
          <span className="flex items-center gap-1">
            <kbd className="rounded border border-ink-200 bg-surface px-1 font-mono">↑↓</kbd>
            navigate
          </span>
          <span className="flex items-center gap-1">
            <kbd className="rounded border border-ink-200 bg-surface px-1 font-mono">↵</kbd>
            open
          </span>
        </div>
      </div>
    </div>
  );
}

/** Registers the Cmd/Ctrl-K and "/" shortcuts. */
export function useCommandPalette() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable;

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
      if (event.key === "/" && !typing) {
        event.preventDefault();
        setOpen(true);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  return { open, setOpen };
}
