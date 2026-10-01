"use client";

import { useQuery } from "@tanstack/react-query";
import { Shield } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { TBody, TD, TH, THead, TR, Table, TableWrapper } from "@/components/ui/table";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import type { Paged } from "@/types/api";

interface AuditLog {
  id: string;
  actor_email?: string | null;
  actor_roles: string[];
  action: string;
  resource_type?: string | null;
  description: string;
  ip_address?: string | null;
  status: string;
  created_at: string;
}

const ACTIONS = [
  "LOGIN", "LOGIN_FAILED", "LOGOUT", "REGISTER", "PASSWORD_CHANGE",
  "PASSWORD_RESET", "PROFILE_UPDATE", "OPPORTUNITY_CREATE", "OPPORTUNITY_UPDATE",
  "APPLICATION_SUBMIT", "APPLICATION_STATUS_CHANGE", "DOCUMENT_UPLOAD",
  "DOCUMENT_ACCESS", "DOCUMENT_DELETE", "ADMIN_ACTION", "ROLE_CHANGE", "EXPORT",
  "ASSESSMENT_SUBMIT",
];

export function AdminAudit() {
  const [action, setAction] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const logs = useQuery({
    queryKey: ["admin", "audit", { action, status, page }],
    queryFn: () =>
      api.paged<AuditLog>("/admin/audit-logs", {
        action: action || undefined,
        status: status || undefined,
        page,
        page_size: 40,
      }) as Promise<Paged<AuditLog>>,
  });

  return (
    <>
      <PageHeader
        title="Audit log"
        description="Append-only record of sensitive actions: sign-ins, profile and role changes, postings, applications, document access, exports and administrative actions."
      />

      <Card className="mb-5 p-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <Select
            label="Action"
            value={action}
            onChange={(event) => {
              setAction(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All actions</option>
            {ACTIONS.map((item) => (
              <option key={item} value={item}>
                {item.replace(/_/g, " ").toLowerCase()}
              </option>
            ))}
          </Select>
          <Select
            label="Outcome"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All outcomes</option>
            <option value="SUCCESS">Success</option>
            <option value="FAILURE">Failure</option>
          </Select>
        </div>
      </Card>

      {logs.isLoading && <SkeletonList count={4} rows={2} />}
      {logs.error && <ErrorState error={logs.error} onRetry={() => void logs.refetch()} />}
      {logs.data?.data.length === 0 && (
        <EmptyState icon={<Shield />} title="No audit entries match those filters" />
      )}

      {logs.data && logs.data.data.length > 0 && (
        <>
          <p className="mb-3 text-sm text-ink-500">{logs.data.meta.total} entries</p>
          <TableWrapper caption="Audit log">
            <Table>
              <THead>
                <TR>
                  <TH>When</TH>
                  <TH>Actor</TH>
                  <TH>Action</TH>
                  <TH>Description</TH>
                  <TH>IP</TH>
                  <TH>Outcome</TH>
                </TR>
              </THead>
              <TBody>
                {logs.data.data.map((log) => (
                  <TR key={log.id}>
                    <TD className="whitespace-nowrap text-xs">
                      {formatDateTime(log.created_at)}
                    </TD>
                    <TD className="text-xs">
                      {log.actor_email ?? "—"}
                      {log.actor_roles.length > 0 && (
                        <span className="block text-2xs text-ink-400">
                          {log.actor_roles.join(", ").toLowerCase()}
                        </span>
                      )}
                    </TD>
                    <TD>
                      <Badge tone="outline">
                        {log.action.replace(/_/g, " ").toLowerCase()}
                      </Badge>
                    </TD>
                    <TD className="max-w-md text-xs">{log.description}</TD>
                    <TD className="font-mono text-2xs">{log.ip_address ?? "—"}</TD>
                    <TD>
                      <Badge tone={log.status === "SUCCESS" ? "success" : "danger"}>
                        {log.status.toLowerCase()}
                      </Badge>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </TableWrapper>

          {logs.data.meta.total_pages > 1 && (
            <nav className="mt-4 flex items-center justify-center gap-2" aria-label="Pagination">
              <Button
                variant="secondary"
                size="sm"
                disabled={!logs.data.meta.has_previous}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="px-2 text-sm text-ink-600">
                Page {logs.data.meta.page} of {logs.data.meta.total_pages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={!logs.data.meta.has_next}
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
