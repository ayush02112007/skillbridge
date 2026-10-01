"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Calendar, MapPin, Users, Video } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, relativeTime } from "@/lib/utils";
import type { EventItem, Paged } from "@/types/api";

const EVENT_TYPES = [
  "WORKSHOP", "GUEST_LECTURE", "HACKATHON", "INDUSTRY_VISIT", "WEBINAR",
  "CAREER_SESSION", "INNOVATION_CHALLENGE", "PANEL_DISCUSSION",
];

function EventCard({
  event,
  onRegister,
  onCancel,
  isPending,
}: {
  event: EventItem;
  onRegister: (id: string) => void;
  onCancel: (id: string) => void;
  isPending: boolean;
}) {
  return (
    <Card className="flex flex-col p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap gap-1.5">
            <Badge tone="brand">{event.event_type.replace(/_/g, " ").toLowerCase()}</Badge>
            {event.grants_certificate && <Badge tone="accent">Certificate</Badge>}
            {!event.has_capacity && !event.is_registered && (
              <Badge tone="warning">Waitlist</Badge>
            )}
          </div>
          <h3 className="mt-2 text-[15px] font-semibold text-ink-900">{event.title}</h3>
          <p className="text-xs text-ink-500">
            {event.company?.name ?? "SkillBridge"}
            {event.speaker_name ? ` · ${event.speaker_name}` : ""}
          </p>
        </div>
      </div>

      <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-ink-600">
        {event.description}
      </p>

      <dl className="mt-3 space-y-1 text-xs text-ink-600">
        <div className="flex items-center gap-1.5">
          <Calendar className="size-3.5 text-ink-400" aria-hidden />
          <dd>{formatDateTime(event.starts_at)} ({relativeTime(event.starts_at)})</dd>
        </div>
        <div className="flex items-center gap-1.5">
          {event.mode === "REMOTE" ? (
            <Video className="size-3.5 text-ink-400" aria-hidden />
          ) : (
            <MapPin className="size-3.5 text-ink-400" aria-hidden />
          )}
          <dd>{event.mode === "REMOTE" ? "Online" : event.venue ?? "On-site"}</dd>
        </div>
        <div className="flex items-center gap-1.5">
          <Users className="size-3.5 text-ink-400" aria-hidden />
          <dd>
            {event.registered_count} registered
            {event.capacity ? ` of ${event.capacity}` : ""}
          </dd>
        </div>
      </dl>

      {event.skill_tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {event.skill_tags.slice(0, 4).map((tag) => (
            <Badge key={tag} tone="neutral">{tag}</Badge>
          ))}
        </div>
      )}

      <div className="mt-auto border-t border-ink-100 pt-3.5 mt-4">
        {event.is_registered ? (
          <div className="flex items-center gap-2">
            <Badge tone="success" size="md">Registered</Badge>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onCancel(event.id)}
            >
              Cancel
            </Button>
            {event.meeting_link && (
              <a href={event.meeting_link} target="_blank" rel="noreferrer" className="ml-auto">
                <Button size="sm" variant="secondary">Join link</Button>
              </a>
            )}
          </div>
        ) : (
          <Button
            block
            size="sm"
            isLoading={isPending}
            onClick={() => onRegister(event.id)}
          >
            {event.has_capacity ? "Register" : "Join waitlist"}
          </Button>
        )}
      </div>
    </Card>
  );
}

export function EventsPage() {
  const queryClient = useQueryClient();
  const [type, setType] = useState("");
  const [pendingId, setPendingId] = useState<string | null>(null);

  const events = useQuery({
    queryKey: ["events", type],
    queryFn: () =>
      api.paged<EventItem>("/events", {
        event_type: type || undefined,
        upcoming_only: true,
        page_size: 24,
      }) as Promise<Paged<EventItem>>,
  });

  const registrations = useQuery({
    queryKey: ["events", "registrations"],
    queryFn: () =>
      api.paged<{ id: string; status: string; event?: EventItem | null; certificate_code?: string | null }>(
        "/events/registrations/mine",
        { page_size: 40 },
      ),
  });

  const register = useMutation({
    mutationFn: (id: string) => api.post(`/events/${id}/register`),
    onSuccess: () => {
      toast.success("Registered");
      setPendingId(null);
      void queryClient.invalidateQueries({ queryKey: ["events"] });
    },
    onError: (error) => {
      setPendingId(null);
      toast.error(error instanceof ApiError ? error.message : "Could not register");
    },
  });

  const cancel = useMutation({
    mutationFn: (id: string) => api.delete(`/events/${id}/register`),
    onSuccess: () => {
      toast.success("Registration cancelled");
      void queryClient.invalidateQueries({ queryKey: ["events"] });
    },
  });

  return (
    <>
      <PageHeader
        title="Workshops & events"
        description="Hands-on workshops, guest lectures, hackathons and career sessions run by industry partners."
      />

      <Tabs defaultValue="upcoming">
        <TabsList ariaLabel="Event views">
          <TabsTrigger value="upcoming">Upcoming</TabsTrigger>
          <TabsTrigger value="mine">
            My registrations
            {registrations.data?.meta.total ? ` (${registrations.data.meta.total})` : ""}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upcoming">
          <div className="mb-4 max-w-xs">
            <Select
              label="Event type"
              value={type}
              onChange={(event) => setType(event.target.value)}
            >
              <option value="">All types</option>
              {EVENT_TYPES.map((item) => (
                <option key={item} value={item}>
                  {item.replace(/_/g, " ").toLowerCase()}
                </option>
              ))}
            </Select>
          </div>

          {events.isLoading && <SkeletonList count={6} rows={3} />}
          {events.error && (
            <ErrorState error={events.error} onRetry={() => void events.refetch()} />
          )}
          {events.data?.data.length === 0 && (
            <EmptyState
              icon={<Calendar />}
              title="No upcoming events"
              description="New workshops and sessions from partner companies will appear here."
            />
          )}

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {events.data?.data.map((event) => (
              <EventCard
                key={event.id}
                event={event}
                isPending={register.isPending && pendingId === event.id}
                onRegister={(id) => {
                  setPendingId(id);
                  register.mutate(id);
                }}
                onCancel={(id) => cancel.mutate(id)}
              />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="mine">
          {registrations.isLoading && <SkeletonList count={3} rows={2} />}
          {registrations.data?.data.length === 0 && (
            <EmptyState
              icon={<Calendar />}
              title="No registrations"
              description="Register for an event and it will appear here with its joining details."
            />
          )}
          <div className="space-y-3">
            {registrations.data?.data.map((registration) => (
              <Card key={registration.id} className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-ink-900">
                      {registration.event?.title}
                    </p>
                    <p className="text-xs text-ink-500">
                      {registration.event
                        ? formatDateTime(registration.event.starts_at)
                        : "—"}
                    </p>
                    {registration.certificate_code && (
                      <p className="mt-1.5 font-mono text-2xs text-success-700">
                        Certificate: {registration.certificate_code}
                      </p>
                    )}
                  </div>
                  <Badge
                    tone={
                      registration.status === "ATTENDED"
                        ? "success"
                        : registration.status === "WAITLISTED"
                          ? "warning"
                          : "brand"
                    }
                    size="md"
                  >
                    {registration.status.toLowerCase()}
                  </Badge>
                </div>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </>
  );
}
