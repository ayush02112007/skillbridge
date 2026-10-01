"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Calendar, MessageSquare, Search, Star, Users } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input, Textarea } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import type { Mentor, MentorRecommendation, Paged } from "@/types/api";

interface MentorshipRequest {
  id: string;
  mentor_id: string;
  mentor?: Mentor | null;
  student_id: string;
  student_name: string;
  topic: string;
  message: string;
  status: string;
  response_message: string;
  sessions: {
    id: string;
    scheduled_at: string;
    duration_minutes: number;
    meeting_link?: string | null;
    agenda: string;
    status: string;
  }[];
  created_at: string;
}

export function MentorshipPanel({ role }: { role: "student" | "mentor" }) {
  const queryClient = useQueryClient();
  const [requestFor, setRequestFor] = useState<Mentor | MentorRecommendation | null>(null);
  const [form, setForm] = useState({ topic: "", message: "" });
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [scheduleFor, setScheduleFor] = useState<MentorshipRequest | null>(null);
  const [slot, setSlot] = useState({ scheduled_at: "", agenda: "", meeting_link: "" });

  const mentors = useQuery({
    queryKey: ["mentors", search],
    queryFn: () =>
      api.paged<Mentor>("/mentorship/mentors", {
        q: search || undefined,
        page_size: 24,
      }) as Promise<Paged<Mentor>>,
    enabled: role === "student",
  });

  const recommended = useQuery({
    queryKey: ["recommendations", "mentors"],
    queryFn: () => api.get<MentorRecommendation[]>("/recommendations/mentors", { limit: 6 }),
    enabled: role === "student",
  });

  const requests = useQuery({
    queryKey: ["mentorship", "requests"],
    queryFn: () =>
      api.paged<MentorshipRequest>("/mentorship/requests", { page_size: 40 }) as Promise<
        Paged<MentorshipRequest>
      >,
  });

  const createRequest = useMutation({
    mutationFn: (mentorId: string) =>
      api.post("/mentorship/requests", {
        mentor_id: mentorId,
        topic: form.topic,
        message: form.message,
      }),
    onSuccess: () => {
      toast.success("Request sent");
      setRequestFor(null);
      setForm({ topic: "", message: "" });
      void queryClient.invalidateQueries({ queryKey: ["mentorship"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not send the request"),
  });

  const respond = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: "ACCEPTED" | "DECLINED" }) =>
      api.post(`/mentorship/requests/${id}/respond`, {
        decision,
        response_message:
          decision === "ACCEPTED"
            ? "Happy to help — let's find a time."
            : "I'm at capacity right now, sorry.",
      }),
    onSuccess: (_result, variables) => {
      toast.success(variables.decision === "ACCEPTED" ? "Request accepted" : "Request declined");
      void queryClient.invalidateQueries({ queryKey: ["mentorship"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not respond"),
  });

  const schedule = useMutation({
    mutationFn: (requestId: string) =>
      api.post(`/mentorship/requests/${requestId}/sessions`, {
        scheduled_at: new Date(slot.scheduled_at).toISOString(),
        duration_minutes: 45,
        agenda: slot.agenda,
        meeting_link: slot.meeting_link || undefined,
      }),
    onSuccess: () => {
      toast.success("Session scheduled and the student notified");
      setScheduleFor(null);
      setSlot({ scheduled_at: "", agenda: "", meeting_link: "" });
      void queryClient.invalidateQueries({ queryKey: ["mentorship"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not schedule"),
  });

  return (
    <>
      <PageHeader
        title="Mentorship"
        description={
          role === "student"
            ? "Talk to people who do the work you want to do. Mentors are matched to the skills you're trying to build."
            : "Requests from students, and the sessions you have scheduled."
        }
      />

      <Tabs defaultValue={role === "student" ? "recommended" : "requests"}>
        <TabsList ariaLabel="Mentorship views">
          {role === "student" && <TabsTrigger value="recommended">Recommended</TabsTrigger>}
          {role === "student" && <TabsTrigger value="browse">Find a mentor</TabsTrigger>}
          <TabsTrigger value="requests">
            {role === "student" ? "My requests" : "Requests"}
          </TabsTrigger>
        </TabsList>

        {role === "student" && (
          <TabsContent value="recommended">
            {recommended.isLoading && <SkeletonList count={3} rows={2} />}
            {recommended.data?.length === 0 && (
              <EmptyState
                icon={<Users />}
                title="No mentor matches yet"
                description="Set a target role and add skills — we'll then match you to mentors who work on exactly those."
              />
            )}
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {recommended.data?.map((mentor) => (
                <Card key={mentor.target_id} className="flex flex-col p-5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex min-w-0 gap-3">
                      <Avatar name={mentor.target_title} size="md" />
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-ink-900">
                          {mentor.target_title}
                        </p>
                        <p className="truncate text-xs text-ink-500">
                          {mentor.designation ?? mentor.headline}
                        </p>
                      </div>
                    </div>
                    <Badge tone="accent">{Math.round(mentor.match_score)}%</Badge>
                  </div>

                  <p className="mt-2 text-xs leading-relaxed text-ink-600">
                    {mentor.reason_summary}
                  </p>
                  <ul className="mt-2 space-y-0.5">
                    {mentor.reasons.slice(0, 2).map((reason) => (
                      <li key={reason} className="text-2xs text-ink-500">• {reason}</li>
                    ))}
                  </ul>

                  <div className="mt-auto flex items-center justify-between gap-2 border-t border-ink-100 pt-3.5 mt-4">
                    <span className="flex items-center gap-1 text-xs text-ink-500">
                      <Star className="size-3.5 fill-accent-400 text-accent-400" aria-hidden />
                      {mentor.rating.toFixed(1)} · {mentor.experience_years}y
                    </span>
                    <Button
                      size="sm"
                      onClick={() => {
                        setRequestFor(mentor as unknown as Mentor);
                        setForm({ topic: "", message: "" });
                      }}
                    >
                      Request
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </TabsContent>
        )}

        {role === "student" && (
          <TabsContent value="browse">
            <Card className="mb-4 p-4">
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  setSearch(query);
                }}
                className="flex items-end gap-3"
              >
                <div className="flex-1">
                  <Input
                    label="Search mentors"
                    leftIcon={<Search />}
                    placeholder="Name, role or focus area"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                </div>
                <Button type="submit">Search</Button>
              </form>
            </Card>

            {mentors.isLoading && <SkeletonList count={6} rows={2} />}
            {mentors.data?.data.length === 0 && (
              <EmptyState icon={<Users />} title="No mentors found" />
            )}
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {mentors.data?.data.map((mentor) => (
                <Card key={mentor.id} className="flex flex-col p-5">
                  <div className="flex gap-3">
                    <Avatar name={mentor.full_name} src={mentor.avatar_url} size="md" />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-ink-900">
                        {mentor.full_name}
                      </p>
                      <p className="truncate text-xs text-ink-500">{mentor.headline}</p>
                    </div>
                  </div>
                  <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-ink-600">
                    {mentor.bio}
                  </p>
                  {mentor.topics.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {mentor.topics.slice(0, 3).map((topic) => (
                        <Badge key={topic} tone="neutral">{topic}</Badge>
                      ))}
                    </div>
                  )}
                  <div className="mt-auto flex items-center justify-between gap-2 border-t border-ink-100 pt-3.5 mt-4">
                    <span className="flex items-center gap-1 text-xs text-ink-500">
                      <Star className="size-3.5 fill-accent-400 text-accent-400" aria-hidden />
                      {mentor.rating.toFixed(1)} · {mentor.sessions_completed} sessions
                    </span>
                    <Button
                      size="sm"
                      disabled={!mentor.is_accepting_requests}
                      onClick={() => {
                        setRequestFor(mentor);
                        setForm({ topic: "", message: "" });
                      }}
                    >
                      {mentor.is_accepting_requests ? "Request" : "At capacity"}
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </TabsContent>
        )}

        <TabsContent value="requests">
          {requests.isLoading && <SkeletonList count={3} rows={2} />}
          {requests.error && (
            <ErrorState error={requests.error} onRetry={() => void requests.refetch()} />
          )}
          {requests.data?.data.length === 0 && (
            <EmptyState
              icon={<MessageSquare />}
              title={role === "student" ? "No requests sent" : "No requests received"}
              description={
                role === "student"
                  ? "Find a mentor and send a specific question — that gets the best response."
                  : "Students who request mentorship from you will appear here."
              }
            />
          )}

          <div className="space-y-3">
            {requests.data?.data.map((request) => (
              <Card key={request.id} className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-ink-900">{request.topic}</p>
                    <p className="text-xs text-ink-500">
                      {role === "student"
                        ? request.mentor?.full_name ?? "Mentor"
                        : request.student_name}
                    </p>
                    {request.message && (
                      <p className="mt-2 text-sm leading-relaxed text-ink-600">
                        {request.message}
                      </p>
                    )}
                    {request.response_message && (
                      <p className="mt-2 rounded-lg bg-surface-muted px-3 py-2 text-xs text-ink-700">
                        {request.response_message}
                      </p>
                    )}
                  </div>
                  <Badge
                    tone={
                      request.status === "COMPLETED"
                        ? "success"
                        : request.status === "DECLINED"
                          ? "danger"
                          : request.status === "REQUESTED"
                            ? "warning"
                            : "brand"
                    }
                    size="md"
                  >
                    {request.status.toLowerCase()}
                  </Badge>
                </div>

                {request.sessions.length > 0 && (
                  <ul className="mt-3 space-y-2 border-t border-ink-100 pt-3">
                    {request.sessions.map((session) => (
                      <li
                        key={session.id}
                        className="flex flex-wrap items-center justify-between gap-2 text-sm"
                      >
                        <span className="flex items-center gap-1.5 text-ink-700">
                          <Calendar className="size-3.5 text-ink-400" aria-hidden />
                          {formatDateTime(session.scheduled_at)} · {session.duration_minutes} min
                        </span>
                        {session.meeting_link && (
                          <a href={session.meeting_link} target="_blank" rel="noreferrer">
                            <Button size="sm" variant="secondary">Join</Button>
                          </a>
                        )}
                      </li>
                    ))}
                  </ul>
                )}

                {role === "mentor" && (
                  <div className="mt-3 flex flex-wrap gap-2 border-t border-ink-100 pt-3">
                    {request.status === "REQUESTED" && (
                      <>
                        <Button
                          size="sm"
                          onClick={() => respond.mutate({ id: request.id, decision: "ACCEPTED" })}
                        >
                          Accept
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => respond.mutate({ id: request.id, decision: "DECLINED" })}
                        >
                          Decline
                        </Button>
                      </>
                    )}
                    {["ACCEPTED", "SCHEDULED"].includes(request.status) && (
                      <Button
                        size="sm"
                        variant="secondary"
                        leftIcon={<Calendar />}
                        onClick={() => setScheduleFor(request)}
                      >
                        Schedule a session
                      </Button>
                    )}
                  </div>
                )}
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {requestFor && (
        <Dialog
          open
          onClose={() => setRequestFor(null)}
          title="Request mentorship"
          description="Be specific — a clear question gets a much better response than 'can you mentor me'."
          footer={
            <>
              <Button variant="secondary" onClick={() => setRequestFor(null)}>Cancel</Button>
              <Button
                disabled={form.topic.trim().length < 3}
                isLoading={createRequest.isPending}
                onClick={() =>
                  createRequest.mutate(
                    "id" in requestFor ? requestFor.id : (requestFor as MentorRecommendation).target_id,
                  )
                }
              >
                Send request
              </Button>
            </>
          }
        >
          <div className="space-y-3">
            <Input
              label="Topic"
              placeholder="e.g. Preparing for backend interviews"
              required
              value={form.topic}
              onChange={(event) => setForm((c) => ({ ...c, topic: event.target.value }))}
            />
            <Textarea
              label="Your message"
              rows={4}
              placeholder="What are you working on, and what specifically would help?"
              value={form.message}
              onChange={(event) => setForm((c) => ({ ...c, message: event.target.value }))}
            />
          </div>
        </Dialog>
      )}

      {scheduleFor && (
        <Dialog
          open
          onClose={() => setScheduleFor(null)}
          title="Schedule a session"
          footer={
            <>
              <Button variant="secondary" onClick={() => setScheduleFor(null)}>Cancel</Button>
              <Button
                disabled={!slot.scheduled_at}
                isLoading={schedule.isPending}
                onClick={() => schedule.mutate(scheduleFor.id)}
              >
                Schedule
              </Button>
            </>
          }
        >
          <div className="space-y-3">
            <Input
              label="Date and time"
              type="datetime-local"
              required
              value={slot.scheduled_at}
              onChange={(event) =>
                setSlot((c) => ({ ...c, scheduled_at: event.target.value }))
              }
            />
            <Input
              label="Agenda"
              placeholder={scheduleFor.topic}
              value={slot.agenda}
              onChange={(event) => setSlot((c) => ({ ...c, agenda: event.target.value }))}
            />
            <Input
              label="Meeting link"
              placeholder="https://meet.example.com/…"
              value={slot.meeting_link}
              onChange={(event) =>
                setSlot((c) => ({ ...c, meeting_link: event.target.value }))
              }
            />
          </div>
        </Dialog>
      )}
    </>
  );
}
