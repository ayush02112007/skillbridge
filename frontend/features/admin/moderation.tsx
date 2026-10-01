"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, Building2, ClipboardCheck, Search, Shield } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TBody, TD, TH, THead, TR, Table, TableWrapper } from "@/components/ui/table";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { AssessmentListItem, Institution, Opportunity, Paged } from "@/types/api";

interface Company {
  id: string;
  name: string;
  slug: string;
  industry_sector: string;
  headquarters_city?: string | null;
  verification_status: string;
  open_positions: number;
}

export function AdminOrganisations() {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");

  const companies = useQuery({
    queryKey: ["admin", "companies", search],
    queryFn: () =>
      api.paged<Company>("/companies", { q: search || undefined, page_size: 40 }) as Promise<
        Paged<Company>
      >,
  });

  const institutions = useQuery({
    queryKey: ["admin", "institutions", search],
    queryFn: () =>
      api.paged<Institution>("/institutions", {
        q: search || undefined,
        page_size: 40,
      }) as Promise<Paged<Institution>>,
  });

  const verifyCompany = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.patch(`/admin/companies/${id}/verification`, { verification_status: status }),
    onSuccess: () => {
      toast.success("Verification updated");
      void queryClient.invalidateQueries({ queryKey: ["admin", "companies"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not update"),
  });

  const verifyInstitution = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.patch(`/admin/institutions/${id}/verification`, { verification_status: status }),
    onSuccess: () => {
      toast.success("Verification updated");
      void queryClient.invalidateQueries({ queryKey: ["admin", "institutions"] });
    },
  });

  return (
    <>
      <PageHeader
        title="Organisations"
        description="Companies and institutions on the platform. Verification is the trust signal students see on every posting."
      />

      <Card className="mb-5 p-4">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setSearch(query);
          }}
          className="flex items-end gap-3"
        >
          <div className="flex-1">
            <Input
              label="Search"
              leftIcon={<Search />}
              placeholder="Organisation name"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <Button type="submit">Search</Button>
        </form>
      </Card>

      <Tabs defaultValue="companies">
        <TabsList ariaLabel="Organisation types">
          <TabsTrigger value="companies">
            Companies{companies.data ? ` (${companies.data.meta.total})` : ""}
          </TabsTrigger>
          <TabsTrigger value="institutions">
            Institutions{institutions.data ? ` (${institutions.data.meta.total})` : ""}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="companies">
          {companies.isLoading && <SkeletonList count={4} rows={1} />}
          {companies.error && (
            <ErrorState error={companies.error} onRetry={() => void companies.refetch()} />
          )}
          {companies.data?.data.length === 0 && (
            <EmptyState icon={<Building2 />} title="No companies found" />
          )}
          {companies.data && companies.data.data.length > 0 && (
            <TableWrapper caption="Companies">
              <Table>
                <THead>
                  <TR>
                    <TH>Company</TH>
                    <TH>Sector</TH>
                    <TH>Open roles</TH>
                    <TH>Verification</TH>
                    <TH><span className="sr-only">Actions</span></TH>
                  </TR>
                </THead>
                <TBody>
                  {companies.data.data.map((company) => (
                    <TR key={company.id}>
                      <TD>
                        <Link
                          href={`/companies/${company.slug}`}
                          className="font-medium text-ink-900 hover:underline"
                        >
                          {company.name}
                        </Link>
                        <p className="text-2xs text-ink-500">
                          {company.headquarters_city ?? "—"}
                        </p>
                      </TD>
                      <TD className="text-xs">{company.industry_sector}</TD>
                      <TD className="tabular-nums">{company.open_positions}</TD>
                      <TD>
                        <Badge
                          tone={
                            company.verification_status === "VERIFIED"
                              ? "success"
                              : company.verification_status === "REJECTED"
                                ? "danger"
                                : "neutral"
                          }
                        >
                          {company.verification_status.toLowerCase()}
                        </Badge>
                      </TD>
                      <TD>
                        <div className="flex justify-end">
                          <Button
                            size="sm"
                            variant="secondary"
                            leftIcon={<BadgeCheck />}
                            onClick={() =>
                              verifyCompany.mutate({
                                id: company.id,
                                status:
                                  company.verification_status === "VERIFIED"
                                    ? "UNVERIFIED"
                                    : "VERIFIED",
                              })
                            }
                          >
                            {company.verification_status === "VERIFIED"
                              ? "Unverify"
                              : "Verify"}
                          </Button>
                        </div>
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </TableWrapper>
          )}
        </TabsContent>

        <TabsContent value="institutions">
          {institutions.isLoading && <SkeletonList count={4} rows={1} />}
          {institutions.data && institutions.data.data.length > 0 && (
            <TableWrapper caption="Institutions">
              <Table>
                <THead>
                  <TR>
                    <TH>Institution</TH>
                    <TH>Location</TH>
                    <TH>Students</TH>
                    <TH>Verification</TH>
                    <TH><span className="sr-only">Actions</span></TH>
                  </TR>
                </THead>
                <TBody>
                  {institutions.data.data.map((institution) => (
                    <TR key={institution.id}>
                      <TD>
                        <p className="font-medium text-ink-900">{institution.name}</p>
                        <p className="text-2xs text-ink-500">
                          {institution.institution_type.replace(/_/g, " ").toLowerCase()}
                        </p>
                      </TD>
                      <TD className="text-xs">
                        {institution.city ?? "—"}
                        {institution.state ? `, ${institution.state}` : ""}
                      </TD>
                      <TD className="tabular-nums">{institution.student_count}</TD>
                      <TD>
                        <Badge
                          tone={
                            institution.verification_status === "VERIFIED"
                              ? "success"
                              : "neutral"
                          }
                        >
                          {institution.verification_status.toLowerCase()}
                        </Badge>
                      </TD>
                      <TD>
                        <div className="flex justify-end">
                          <Button
                            size="sm"
                            variant="secondary"
                            leftIcon={<BadgeCheck />}
                            onClick={() =>
                              verifyInstitution.mutate({
                                id: institution.id,
                                status:
                                  institution.verification_status === "VERIFIED"
                                    ? "UNVERIFIED"
                                    : "VERIFIED",
                              })
                            }
                          >
                            {institution.verification_status === "VERIFIED"
                              ? "Unverify"
                              : "Verify"}
                          </Button>
                        </div>
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </TableWrapper>
          )}
        </TabsContent>
      </Tabs>
    </>
  );
}

export function AdminModeration() {
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");

  const opportunities = useQuery({
    queryKey: ["admin", "opportunities"],
    queryFn: () =>
      api.paged<Opportunity>("/opportunities", {
        page_size: 40,
        open_only: false,
      }) as Promise<Paged<Opportunity>>,
  });

  const moderate = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.post(`/admin/opportunities/${id}/moderate?status=${status}&reason=${encodeURIComponent(reason)}`),
    onSuccess: () => {
      toast.success("Posting moderated");
      setReason("");
      void queryClient.invalidateQueries({ queryKey: ["admin", "opportunities"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not moderate"),
  });

  return (
    <>
      <PageHeader
        title="Moderation"
        description="Every posting on the platform. Taking one down is recorded in the audit trail with its reason."
      />

      <Card className="mb-5 p-4">
        <Input
          label="Reason for the next moderation action"
          placeholder="e.g. Misleading compensation"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
        />
      </Card>

      {opportunities.isLoading && <SkeletonList count={4} rows={1} />}
      {opportunities.error && (
        <ErrorState
          error={opportunities.error}
          onRetry={() => void opportunities.refetch()}
        />
      )}
      {opportunities.data?.data.length === 0 && (
        <EmptyState icon={<Shield />} title="No postings on the platform yet" />
      )}

      {opportunities.data && opportunities.data.data.length > 0 && (
        <TableWrapper caption="Postings">
          <Table>
            <THead>
              <TR>
                <TH>Posting</TH>
                <TH>Company</TH>
                <TH>Type</TH>
                <TH>Status</TH>
                <TH>Applications</TH>
                <TH><span className="sr-only">Actions</span></TH>
              </TR>
            </THead>
            <TBody>
              {opportunities.data.data.map((posting) => (
                <TR key={posting.id}>
                  <TD>
                    <Link
                      href={`/opportunities/${posting.id}`}
                      className="font-medium text-ink-900 hover:underline"
                    >
                      {posting.title}
                    </Link>
                    <p className="text-2xs text-ink-500">
                      {posting.published_at ? formatDate(posting.published_at) : "Not published"}
                    </p>
                  </TD>
                  <TD className="text-xs">{posting.company?.name}</TD>
                  <TD>
                    <Badge tone="outline">
                      {posting.opportunity_type.replace(/_/g, " ").toLowerCase()}
                    </Badge>
                  </TD>
                  <TD>
                    <Badge
                      tone={posting.status === "PUBLISHED" ? "success" : "neutral"}
                    >
                      {posting.status.toLowerCase()}
                    </Badge>
                  </TD>
                  <TD className="tabular-nums">{posting.applications_count}</TD>
                  <TD>
                    <div className="flex justify-end">
                      {posting.status === "PUBLISHED" ? (
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() =>
                            moderate.mutate({ id: posting.id, status: "ARCHIVED" })
                          }
                        >
                          Take down
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() =>
                            moderate.mutate({ id: posting.id, status: "PUBLISHED" })
                          }
                        >
                          Restore
                        </Button>
                      )}
                    </div>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </TableWrapper>
      )}
    </>
  );
}

export function AdminAssessments() {
  const assessments = useQuery({
    queryKey: ["admin", "assessments"],
    queryFn: () =>
      api.paged<AssessmentListItem>("/assessments", { page_size: 40 }) as Promise<
        Paged<AssessmentListItem>
      >,
  });

  return (
    <>
      <PageHeader
        title="Assessments"
        description="The assessment catalogue. Every question is tied to a skill, which is what turns a result into a measured skill profile."
      />

      {assessments.isLoading && <SkeletonList count={4} rows={1} />}
      {assessments.error && (
        <ErrorState error={assessments.error} onRetry={() => void assessments.refetch()} />
      )}
      {assessments.data?.data.length === 0 && (
        <EmptyState icon={<ClipboardCheck />} title="No assessments published" />
      )}

      {assessments.data && assessments.data.data.length > 0 && (
        <TableWrapper caption="Assessments">
          <Table>
            <THead>
              <TR>
                <TH>Assessment</TH>
                <TH>Type</TH>
                <TH>Domain</TH>
                <TH>Questions</TH>
                <TH>Duration</TH>
                <TH>Pass mark</TH>
              </TR>
            </THead>
            <TBody>
              {assessments.data.data.map((assessment) => (
                <TR key={assessment.id}>
                  <TD>
                    <p className="font-medium text-ink-900">{assessment.title}</p>
                    <p className="max-w-md truncate text-2xs text-ink-500">
                      {assessment.description}
                    </p>
                  </TD>
                  <TD>
                    <Badge tone="brand">
                      {assessment.assessment_type.replace(/_/g, " ").toLowerCase()}
                    </Badge>
                  </TD>
                  <TD className="text-xs">{assessment.domain ?? "—"}</TD>
                  <TD className="tabular-nums">{assessment.question_count}</TD>
                  <TD className="tabular-nums">{assessment.duration_minutes} min</TD>
                  <TD className="tabular-nums">{assessment.passing_score}%</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </TableWrapper>
      )}
    </>
  );
}
