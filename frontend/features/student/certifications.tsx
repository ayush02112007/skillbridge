"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Award, ExternalLink, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/utils";

interface Certification {
  id: string;
  name: string;
  issuer: string;
  credential_id?: string | null;
  credential_url?: string | null;
  issued_on?: string | null;
  expires_on?: string | null;
  verification_status: string;
  created_at: string;
}

export function StudentCertifications() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    name: "", issuer: "", credential_id: "", credential_url: "", issued_on: "",
  });

  const list = useQuery({
    queryKey: ["certifications"],
    queryFn: () => api.get<Certification[]>("/learning/certifications"),
  });

  const create = useMutation({
    mutationFn: () =>
      api.post("/learning/certifications", {
        ...form,
        credential_id: form.credential_id || undefined,
        credential_url: form.credential_url || undefined,
        issued_on: form.issued_on || undefined,
      }),
    onSuccess: () => {
      toast.success("Certification added");
      setOpen(false);
      setForm({ name: "", issuer: "", credential_id: "", credential_url: "", issued_on: "" });
      void queryClient.invalidateQueries({ queryKey: ["certifications"] });
      void queryClient.invalidateQueries({ queryKey: ["student"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not add"),
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.delete(`/learning/certifications/${id}`),
    onSuccess: () => {
      toast.success("Removed");
      void queryClient.invalidateQueries({ queryKey: ["certifications"] });
    },
  });

  return (
    <>
      <PageHeader
        title="Certifications"
        description="Certifications you have earned. Ones awarded for completing a SkillBridge programme are verified automatically; self-added ones can be verified by your institution."
        actions={
          <Button onClick={() => setOpen(true)} leftIcon={<Plus />}>
            Add certification
          </Button>
        }
      />

      {list.isLoading && <SkeletonList count={3} rows={1} />}
      {list.error && <ErrorState error={list.error} onRetry={() => void list.refetch()} />}
      {list.data?.length === 0 && (
        <EmptyState
          icon={<Award />}
          title="No certifications yet"
          description="Complete a learning programme, or add a certification you earned elsewhere."
          action={
            <Button size="sm" onClick={() => setOpen(true)} leftIcon={<Plus />}>
              Add your first
            </Button>
          }
        />
      )}

      <div className="space-y-3">
        {list.data?.map((certification) => (
          <Card key={certification.id} className="flex flex-wrap items-center gap-3 p-4">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-accent-50 text-accent-700">
              <Award className="size-4" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink-900">
                {certification.name}
                <Badge
                  tone={certification.verification_status === "VERIFIED" ? "success" : "neutral"}
                >
                  {certification.verification_status.toLowerCase()}
                </Badge>
              </p>
              <p className="text-xs text-ink-500">
                {certification.issuer}
                {certification.issued_on ? ` · ${formatDate(certification.issued_on)}` : ""}
              </p>
            </div>
            {certification.credential_url && (
              <a href={certification.credential_url} target="_blank" rel="noreferrer">
                <Button size="sm" variant="ghost" aria-label="View credential">
                  <ExternalLink />
                </Button>
              </a>
            )}
            <Button
              size="sm"
              variant="ghost"
              aria-label="Remove"
              onClick={() => remove.mutate(certification.id)}
              className="text-ink-400 hover:text-danger-600"
            >
              <Trash2 />
            </Button>
          </Card>
        ))}
      </div>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Add a certification"
        description="Adding the credential link makes it much easier for an institution to verify."
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button
              disabled={!form.name || !form.issuer}
              isLoading={create.isPending}
              onClick={() => create.mutate()}
            >
              Add
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Input
            label="Certification name"
            required
            placeholder="AWS Certified Cloud Practitioner"
            value={form.name}
            onChange={(event) => setForm((c) => ({ ...c, name: event.target.value }))}
          />
          <Input
            label="Issuer"
            required
            placeholder="Amazon Web Services"
            value={form.issuer}
            onChange={(event) => setForm((c) => ({ ...c, issuer: event.target.value }))}
          />
          <Input
            label="Credential ID"
            value={form.credential_id}
            onChange={(event) => setForm((c) => ({ ...c, credential_id: event.target.value }))}
          />
          <Input
            label="Credential URL"
            placeholder="https://…"
            value={form.credential_url}
            onChange={(event) => setForm((c) => ({ ...c, credential_url: event.target.value }))}
          />
          <Input
            label="Issued on"
            type="date"
            value={form.issued_on}
            onChange={(event) => setForm((c) => ({ ...c, issued_on: event.target.value }))}
          />
        </div>
      </Dialog>
    </>
  );
}
