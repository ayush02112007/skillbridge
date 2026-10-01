"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Download, FileText, Lock, ShieldCheck, Sparkles, Trash2, Upload,
} from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { Select } from "@/components/ui/input";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, apiRequest, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { JobRole, Paged } from "@/types/api";

interface DocumentItem {
  id: string;
  document_type: string;
  title: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  visibility: string;
  scan_status: string;
  is_primary_resume: boolean;
  extraction_status: string;
  created_at: string;
  download_url?: string | null;
}

interface ResumeAnalysis {
  id: string;
  ats_score: number;
  extracted_skills: { skill_name: string; occurrences: number; is_aspirational: boolean }[];
  matched_skills: string[];
  missing_skills: string[];
  suggestions: string[];
  analyzed_by: string;
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function StudentDocuments() {
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const [documentType, setDocumentType] = useState("RESUME");
  const [analysis, setAnalysis] = useState<ResumeAnalysis | null>(null);
  const [analysingId, setAnalysingId] = useState<string | null>(null);

  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: () =>
      api.paged<DocumentItem>("/documents", { page_size: 40 }) as Promise<Paged<DocumentItem>>,
  });

  const roles = useQuery({
    queryKey: ["job-roles", "documents"],
    queryFn: () => api.paged<JobRole>("/job-roles", { page_size: 60 }) as Promise<Paged<JobRole>>,
    staleTime: 10 * 60_000,
  });

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const body = new FormData();
      body.append("file", file);
      body.append("document_type", documentType);
      body.append("title", file.name);
      return apiRequest<DocumentItem>("/documents", { method: "POST", body });
    },
    onSuccess: () => {
      toast.success("Uploaded");
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      void queryClient.invalidateQueries({ queryKey: ["student"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Upload failed"),
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.delete(`/documents/${id}`),
    onSuccess: () => {
      toast.success("Deleted");
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const analyse = useMutation({
    mutationFn: ({ id, roleId }: { id: string; roleId?: string }) =>
      api.post<ResumeAnalysis>(`/documents/${id}/analyse`, {
        job_role_id: roleId || undefined,
        import_skills: false,
      }),
    onSuccess: (result) => {
      setAnalysis(result);
      setAnalysingId(null);
    },
    onError: (error) => {
      setAnalysingId(null);
      toast.error(error instanceof ApiError ? error.message : "Could not analyse");
    },
  });

  return (
    <>
      <PageHeader
        title="Documents"
        description="Your resume, certificates and supporting files. Everything is private by default — recruiters only ever see a resume you attached to an application with their company."
        actions={
          <>
            <Select
              aria-label="Document type"
              value={documentType}
              onChange={(event) => setDocumentType(event.target.value)}
              className="w-44"
            >
              <option value="RESUME">Resume</option>
              <option value="CERTIFICATE">Certificate</option>
              <option value="MARKSHEET">Mark sheet</option>
              <option value="PROJECT_REPORT">Project report</option>
              <option value="OTHER">Other</option>
            </Select>
            <Button
              onClick={() => fileInput.current?.click()}
              isLoading={upload.isPending}
              leftIcon={<Upload />}
            >
              Upload
            </Button>
          </>
        }
      />

      <input
        ref={fileInput}
        type="file"
        accept=".pdf,.docx,.png,.jpg,.jpeg"
        className="sr-only"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) upload.mutate(file);
          event.target.value = "";
        }}
      />

      <Card className="mb-5 border-brand-200 bg-brand-50/50 p-4">
        <div className="flex gap-3">
          <ShieldCheck className="mt-0.5 size-5 shrink-0 text-brand-700" aria-hidden />
          <div className="text-sm text-brand-900">
            <p className="font-medium">How your files are handled</p>
            <p className="mt-0.5 text-xs leading-relaxed">
              PDF, DOCX, PNG and JPG only, up to 10 MB. Every upload is checked
              against its declared type, stored under an opaque key, and served
              through short-lived signed links. Access is logged.
            </p>
          </div>
        </div>
      </Card>

      {documents.isLoading && <SkeletonList count={3} rows={2} />}
      {documents.error && (
        <ErrorState error={documents.error} onRetry={() => void documents.refetch()} />
      )}

      {documents.data?.data.length === 0 && (
        <EmptyState
          icon={<FileText />}
          title="No documents uploaded"
          description="Upload your resume to attach it to applications and to get an analysis against your target role."
          action={
            <Button size="sm" onClick={() => fileInput.current?.click()} leftIcon={<Upload />}>
              Upload your resume
            </Button>
          }
        />
      )}

      {documents.data && documents.data.data.length > 0 && (
        <div className="space-y-3">
          {documents.data.data.map((document) => (
            <Card key={document.id} className="p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex min-w-0 gap-3">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-ink-100 text-ink-500">
                    <FileText className="size-4" aria-hidden />
                  </span>
                  <div className="min-w-0">
                    <p className="flex flex-wrap items-center gap-2 truncate text-sm font-medium text-ink-900">
                      {document.title}
                      {document.is_primary_resume && <Badge tone="brand">Primary resume</Badge>}
                    </p>
                    <p className="text-xs text-ink-500">
                      {document.document_type.replace(/_/g, " ").toLowerCase()} ·{" "}
                      {formatBytes(document.size_bytes)} · {formatDate(document.created_at)}
                    </p>
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      <Badge tone="neutral">
                        <Lock className="size-3" aria-hidden />
                        {document.visibility.replace(/_/g, " ").toLowerCase()}
                      </Badge>
                      {document.scan_status !== "SKIPPED" && (
                        <Badge tone={document.scan_status === "CLEAN" ? "success" : "warning"}>
                          scan: {document.scan_status.toLowerCase()}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex shrink-0 flex-wrap gap-2">
                  {document.document_type === "RESUME" && (
                    <Button
                      size="sm"
                      variant="secondary"
                      leftIcon={<Sparkles />}
                      isLoading={analyse.isPending && analysingId === document.id}
                      onClick={() => {
                        setAnalysingId(document.id);
                        analyse.mutate({ id: document.id });
                      }}
                    >
                      Analyse
                    </Button>
                  )}
                  {document.download_url && (
                    <a href={document.download_url} target="_blank" rel="noreferrer">
                      <Button size="sm" variant="ghost" aria-label="Download">
                        <Download />
                      </Button>
                    </a>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    aria-label="Delete"
                    onClick={() => remove.mutate(document.id)}
                    className="text-ink-400 hover:text-danger-600"
                  >
                    <Trash2 />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {analysis && (
        <Dialog
          open
          onClose={() => setAnalysis(null)}
          title="Resume analysis"
          description="Extracted by exact matching against the skill taxonomy — nothing is invented."
          size="lg"
          footer={<Button onClick={() => setAnalysis(null)}>Close</Button>}
        >
          <div className="space-y-5">
            <div>
              <Progress
                value={analysis.ats_score}
                label="Machine-readability score"
                showValue
              />
              <p className="mt-1.5 text-xs text-ink-500">
                Based on concrete, checkable properties: section headings, contact
                details, links, length and skill coverage.
              </p>
            </div>

            <div>
              <p className="mb-2 text-sm font-semibold text-ink-900">
                Skills found in your resume
              </p>
              <div className="flex flex-wrap gap-1">
                {analysis.extracted_skills.length === 0 && (
                  <p className="text-sm text-ink-500">
                    No taxonomy skills were detected. Add an explicit Skills
                    section naming the technologies you use.
                  </p>
                )}
                {analysis.extracted_skills.map((skill) => (
                  <Badge
                    key={skill.skill_name}
                    tone={skill.is_aspirational ? "warning" : "success"}
                  >
                    {skill.skill_name}
                    {skill.is_aspirational ? " (learning)" : ""}
                  </Badge>
                ))}
              </div>
            </div>

            {analysis.missing_skills.length > 0 && (
              <div>
                <p className="mb-2 text-sm font-semibold text-ink-900">
                  Expected by your target role but not in the resume
                </p>
                <div className="flex flex-wrap gap-1">
                  {analysis.missing_skills.map((skill) => (
                    <Badge key={skill} tone="danger">{skill}</Badge>
                  ))}
                </div>
              </div>
            )}

            <div>
              <p className="mb-2 text-sm font-semibold text-ink-900">Suggestions</p>
              <ul className="space-y-1.5">
                {analysis.suggestions.map((suggestion) => (
                  <li key={suggestion} className="flex gap-2 text-sm leading-relaxed text-ink-700">
                    <span className="mt-1.5 size-1 shrink-0 rounded-full bg-brand-500" aria-hidden />
                    {suggestion}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Dialog>
      )}
    </>
  );
}
