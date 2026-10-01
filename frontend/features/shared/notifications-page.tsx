"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox, Select } from "@/components/ui/input";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { cn, relativeTime } from "@/lib/utils";
import type { NotificationItem, Paged } from "@/types/api";

const CATEGORIES = [
  "APPLICATION", "OPPORTUNITY", "LEARNING", "MENTORSHIP", "EVENT",
  "ASSESSMENT", "MESSAGE", "SYSTEM",
];

interface Preference {
  category: string;
  channel: string;
  is_enabled: boolean;
}

export function NotificationsPage() {
  const queryClient = useQueryClient();
  const [category, setCategory] = useState("");
  const [unreadOnly, setUnreadOnly] = useState(false);

  const notifications = useQuery({
    queryKey: ["notifications", "page", category, unreadOnly],
    queryFn: () =>
      api.paged<NotificationItem>("/notifications", {
        category: category || undefined,
        unread_only: unreadOnly || undefined,
        page_size: 50,
      }) as Promise<Paged<NotificationItem>>,
  });

  const preferences = useQuery({
    queryKey: ["notifications", "preferences"],
    queryFn: () => api.get<Preference[]>("/notifications/preferences"),
  });

  const markRead = useMutation({
    mutationFn: (ids?: string[]) =>
      api.post("/notifications/read", { notification_ids: ids ?? null }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const savePreferences = useMutation({
    mutationFn: (updated: Preference[]) =>
      api.put<Preference[]>("/notifications/preferences", { preferences: updated }),
    onSuccess: () => {
      toast.success("Preferences saved");
      void queryClient.invalidateQueries({ queryKey: ["notifications", "preferences"] });
    },
  });

  const togglePreference = (preference: Preference) => {
    savePreferences.mutate([{ ...preference, is_enabled: !preference.is_enabled }]);
  };

  const byCategory = (preferences.data ?? []).reduce<Record<string, Preference[]>>(
    (acc, preference) => {
      (acc[preference.category] ??= []).push(preference);
      return acc;
    },
    {},
  );

  return (
    <>
      <PageHeader
        title="Notifications"
        description="Updates about your applications, mentorship, learning and events."
        actions={
          <Button
            variant="secondary"
            leftIcon={<CheckCheck />}
            onClick={() => markRead.mutate(undefined)}
          >
            Mark all read
          </Button>
        }
      />

      <Tabs defaultValue="all">
        <TabsList ariaLabel="Notification views">
          <TabsTrigger value="all">All notifications</TabsTrigger>
          <TabsTrigger value="preferences">Preferences</TabsTrigger>
        </TabsList>

        <TabsContent value="all">
          <div className="mb-4 flex flex-wrap items-end gap-4">
            <Select
              label="Category"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              className="w-56"
            >
              <option value="">All categories</option>
              {CATEGORIES.map((item) => (
                <option key={item} value={item}>
                  {item.replace(/_/g, " ").toLowerCase()}
                </option>
              ))}
            </Select>
            <div className="pb-2">
              <Checkbox
                label="Unread only"
                checked={unreadOnly}
                onChange={(event) => setUnreadOnly(event.target.checked)}
              />
            </div>
          </div>

          {notifications.isLoading && <SkeletonList count={5} rows={2} />}
          {notifications.error && (
            <ErrorState
              error={notifications.error}
              onRetry={() => void notifications.refetch()}
            />
          )}
          {notifications.data?.data.length === 0 && (
            <EmptyState
              icon={<Bell />}
              title="Nothing here"
              description={
                unreadOnly
                  ? "You have read everything."
                  : "Notifications about your activity will appear here."
              }
            />
          )}

          <ul className="space-y-2">
            {notifications.data?.data.map((item) => {
              const content = (
                <div className="flex gap-3">
                  <span
                    className={cn(
                      "mt-1 size-2 shrink-0 rounded-full",
                      item.read_at ? "bg-ink-200" : "bg-brand-600",
                    )}
                    aria-hidden
                  />
                  <div className="min-w-0 flex-1">
                    <p
                      className={cn(
                        "text-sm",
                        item.read_at ? "text-ink-600" : "font-medium text-ink-900",
                      )}
                    >
                      {item.title}
                    </p>
                    {item.body && (
                      <p className="mt-0.5 text-xs text-ink-500">{item.body}</p>
                    )}
                    <div className="mt-1.5 flex items-center gap-2">
                      <Badge tone="outline">
                        {item.category.replace(/_/g, " ").toLowerCase()}
                      </Badge>
                      <span className="text-2xs text-ink-400">
                        {relativeTime(item.created_at)}
                      </span>
                    </div>
                  </div>
                </div>
              );

              return (
                <li key={item.id}>
                  <Card className="p-4">
                    {item.action_url ? (
                      <Link
                        href={item.action_url}
                        onClick={() => !item.read_at && markRead.mutate([item.id])}
                      >
                        {content}
                      </Link>
                    ) : (
                      content
                    )}
                  </Card>
                </li>
              );
            })}
          </ul>
        </TabsContent>

        <TabsContent value="preferences">
          <Card className="p-5">
            <p className="mb-4 text-sm text-ink-600">
              Choose how you hear about each kind of update. In-app notifications
              always appear in the bell menu; email is sent only where enabled.
            </p>
            <div className="space-y-4">
              {Object.entries(byCategory).map(([categoryName, entries]) => (
                <div
                  key={categoryName}
                  className="flex flex-wrap items-center justify-between gap-4 border-b border-ink-100 pb-4 last:border-0"
                >
                  <p className="text-sm font-medium capitalize text-ink-900">
                    {categoryName.replace(/_/g, " ").toLowerCase()}
                  </p>
                  <div className="flex gap-5">
                    {entries.map((preference) => (
                      <Checkbox
                        key={`${preference.category}-${preference.channel}`}
                        label={preference.channel === "IN_APP" ? "In-app" : "Email"}
                        checked={preference.is_enabled}
                        onChange={() => togglePreference(preference)}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </>
  );
}
