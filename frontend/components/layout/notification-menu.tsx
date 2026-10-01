"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Award, Bell, Briefcase, Calendar, CheckCheck, GraduationCap, Info,
  MessageSquare, Users,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/states";
import { api } from "@/lib/api";
import { cn, relativeTime } from "@/lib/utils";
import type { NotificationItem, Paged } from "@/types/api";

const CATEGORY_ICON: Record<string, React.ReactNode> = {
  APPLICATION: <Briefcase />,
  OPPORTUNITY: <Briefcase />,
  LEARNING: <GraduationCap />,
  MENTORSHIP: <Users />,
  EVENT: <Calendar />,
  ASSESSMENT: <Award />,
  MESSAGE: <MessageSquare />,
  SYSTEM: <Info />,
};

export function NotificationMenu() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const { data: summary } = useQuery({
    queryKey: ["notifications", "summary"],
    queryFn: () => api.get<{ unread: number; by_category: Record<string, number> }>(
      "/notifications/summary",
    ),
    refetchInterval: 60_000,
  });

  const { data: page, isLoading } = useQuery({
    queryKey: ["notifications", "list"],
    queryFn: () =>
      api.paged<NotificationItem>("/notifications", { page_size: 10 }) as Promise<
        Paged<NotificationItem>
      >,
    enabled: open,
  });

  const markRead = useMutation({
    mutationFn: (ids?: string[]) =>
      api.post("/notifications/read", { notification_ids: ids ?? null }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const unread = summary?.unread ?? 0;

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
        aria-expanded={open}
        aria-haspopup="menu"
        className="relative rounded-lg p-2 text-ink-600 transition-colors hover:bg-ink-100 hover:text-ink-900"
      >
        <Bell className="size-[18px]" />
        {unread > 0 && (
          <span className="absolute right-1 top-1 flex min-w-4 items-center justify-center rounded-full bg-danger-600 px-1 text-2xs font-semibold leading-4 text-white">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-2 w-[22rem] max-w-[calc(100vw-2rem)] animate-slide-up overflow-hidden rounded-2xl border border-ink-200 bg-surface shadow-popover"
        >
          <div className="flex items-center justify-between border-b border-ink-100 px-4 py-3">
            <h2 className="text-sm font-semibold text-ink-900">Notifications</h2>
            {unread > 0 && (
              <Button
                variant="link"
                size="sm"
                onClick={() => markRead.mutate(undefined)}
                leftIcon={<CheckCheck />}
                className="text-xs"
              >
                Mark all read
              </Button>
            )}
          </div>

          <div className="max-h-[22rem] overflow-y-auto">
            {isLoading && (
              <p className="px-4 py-8 text-center text-sm text-ink-400">Loading…</p>
            )}
            {!isLoading && !page?.data.length && (
              <EmptyState
                className="border-0 bg-transparent py-8"
                icon={<Bell />}
                title="You're all caught up"
                description="Updates about your applications, mentorship and events appear here."
              />
            )}
            {page?.data.map((item) => {
              const body = (
                <div className="flex gap-3">
                  <span
                    className={cn(
                      "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg [&_svg]:size-4",
                      item.read_at ? "bg-ink-100 text-ink-400" : "bg-brand-50 text-brand-700",
                    )}
                    aria-hidden
                  >
                    {CATEGORY_ICON[item.category] ?? <Info />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span
                      className={cn(
                        "block text-sm leading-snug",
                        item.read_at ? "text-ink-600" : "font-medium text-ink-900",
                      )}
                    >
                      {item.title}
                    </span>
                    {item.body && (
                      <span className="mt-0.5 block truncate text-xs text-ink-500">
                        {item.body}
                      </span>
                    )}
                    <span className="mt-1 block text-2xs text-ink-400">
                      {relativeTime(item.created_at)}
                    </span>
                  </span>
                  {!item.read_at && (
                    <span className="mt-2 size-1.5 shrink-0 rounded-full bg-brand-600" aria-hidden />
                  )}
                </div>
              );

              return item.action_url ? (
                <Link
                  key={item.id}
                  href={item.action_url}
                  onClick={() => {
                    markRead.mutate([item.id]);
                    setOpen(false);
                  }}
                  className="block border-b border-ink-50 px-4 py-3 transition-colors last:border-0 hover:bg-surface-muted"
                >
                  {body}
                </Link>
              ) : (
                <div key={item.id} className="border-b border-ink-50 px-4 py-3 last:border-0">
                  {body}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
