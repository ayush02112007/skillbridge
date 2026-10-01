"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, ShieldOff, UserCheck, Users } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input, Select } from "@/components/ui/input";
import { TBody, TD, TH, THead, TR, Table, TableWrapper } from "@/components/ui/table";
import { EmptyState, ErrorState, SkeletonList } from "@/components/ui/states";
import { api, ApiError } from "@/lib/api";
import { ROLE_LABELS } from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import type { Institution, Paged, RoleName, User } from "@/types/api";

export function AdminUsers() {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({
    email: "", password: "", full_name: "", role: "INSTITUTION_ADMIN" as RoleName,
    institution_id: "",
  });

  const users = useQuery({
    queryKey: ["admin", "users", { search, role, status, page }],
    queryFn: () =>
      api.paged<User>("/admin/users", {
        q: search || undefined,
        role: role || undefined,
        status: status || undefined,
        page,
        page_size: 25,
      }) as Promise<Paged<User>>,
  });

  const institutions = useQuery({
    queryKey: ["institutions", "admin"],
    queryFn: () =>
      api.paged<Institution>("/institutions", { page_size: 60 }) as Promise<Paged<Institution>>,
  });

  const createUser = useMutation({
    mutationFn: () =>
      api.post<User>("/admin/users", {
        ...form,
        institution_id: form.institution_id || undefined,
      }),
    onSuccess: () => {
      toast.success("Account provisioned");
      setCreateOpen(false);
      setForm({
        email: "", password: "", full_name: "",
        role: "INSTITUTION_ADMIN", institution_id: "",
      });
      void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not create the account"),
  });

  const changeStatus = useMutation({
    mutationFn: ({ id, newStatus }: { id: string; newStatus: string }) =>
      api.patch(`/admin/users/${id}/status`, { status: newStatus, reason: "Admin action" }),
    onSuccess: () => {
      toast.success("Status updated");
      void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not update"),
  });

  return (
    <>
      <PageHeader
        title="Users"
        description="Every account on the platform. Institution and platform admins are provisioned here — they cannot self-register."
        actions={
          <Button onClick={() => setCreateOpen(true)} leftIcon={<Plus />}>
            Provision account
          </Button>
        }
      />

      <Card className="mb-5 p-4">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setSearch(query);
            setPage(1);
          }}
          className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
        >
          <Input
            label="Search"
            leftIcon={<Search />}
            placeholder="Name or email"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <Select
            label="Role"
            value={role}
            onChange={(event) => {
              setRole(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All roles</option>
            {Object.entries(ROLE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </Select>
          <Select
            label="Status"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="PENDING_VERIFICATION">Pending verification</option>
            <option value="SUSPENDED">Suspended</option>
            <option value="DEACTIVATED">Deactivated</option>
          </Select>
          <div className="flex items-end">
            <Button type="submit" block>Filter</Button>
          </div>
        </form>
      </Card>

      {users.isLoading && <SkeletonList count={4} rows={2} />}
      {users.error && <ErrorState error={users.error} onRetry={() => void users.refetch()} />}
      {users.data?.data.length === 0 && (
        <EmptyState icon={<Users />} title="No accounts match those filters" />
      )}

      {users.data && users.data.data.length > 0 && (
        <>
          <p className="mb-3 text-sm text-ink-500">{users.data.meta.total} accounts</p>
          <TableWrapper caption="Users">
            <Table>
              <THead>
                <TR>
                  <TH>Account</TH>
                  <TH>Roles</TH>
                  <TH>Status</TH>
                  <TH>Joined</TH>
                  <TH>Last sign-in</TH>
                  <TH><span className="sr-only">Actions</span></TH>
                </TR>
              </THead>
              <TBody>
                {users.data.data.map((user) => (
                  <TR key={user.id}>
                    <TD>
                      <div className="flex items-center gap-2.5">
                        <Avatar name={user.full_name} src={user.avatar_url} size="sm" />
                        <div className="min-w-0">
                          <p className="truncate font-medium text-ink-900">
                            {user.full_name}
                          </p>
                          <p className="truncate text-2xs text-ink-500">{user.email}</p>
                        </div>
                      </div>
                    </TD>
                    <TD>
                      <div className="flex flex-wrap gap-1">
                        {user.roles.map((entry) => (
                          <Badge key={entry.name} tone="brand">
                            {ROLE_LABELS[entry.name]}
                          </Badge>
                        ))}
                      </div>
                    </TD>
                    <TD>
                      <Badge
                        tone={
                          user.status === "ACTIVE"
                            ? "success"
                            : user.status === "SUSPENDED"
                              ? "danger"
                              : "neutral"
                        }
                      >
                        {user.status.replace(/_/g, " ").toLowerCase()}
                      </Badge>
                    </TD>
                    <TD className="whitespace-nowrap text-xs">
                      {formatDate(user.created_at)}
                    </TD>
                    <TD className="whitespace-nowrap text-xs">
                      {user.last_login_at ? formatDate(user.last_login_at) : "Never"}
                    </TD>
                    <TD>
                      <div className="flex justify-end">
                        {user.status === "ACTIVE" ? (
                          <Button
                            size="sm"
                            variant="secondary"
                            leftIcon={<ShieldOff />}
                            onClick={() =>
                              changeStatus.mutate({ id: user.id, newStatus: "SUSPENDED" })
                            }
                          >
                            Suspend
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            variant="secondary"
                            leftIcon={<UserCheck />}
                            onClick={() =>
                              changeStatus.mutate({ id: user.id, newStatus: "ACTIVE" })
                            }
                          >
                            Reactivate
                          </Button>
                        )}
                      </div>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </TableWrapper>

          {users.data.meta.total_pages > 1 && (
            <nav className="mt-4 flex items-center justify-center gap-2" aria-label="Pagination">
              <Button
                variant="secondary"
                size="sm"
                disabled={!users.data.meta.has_previous}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="px-2 text-sm text-ink-600">
                Page {users.data.meta.page} of {users.data.meta.total_pages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={!users.data.meta.has_next}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </nav>
          )}
        </>
      )}

      <Dialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Provision an account"
        description="Used for institution administrators and platform staff, who cannot register themselves."
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button
              disabled={!form.email || !form.full_name || form.password.length < 10}
              isLoading={createUser.isPending}
              onClick={() => createUser.mutate()}
            >
              Create account
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Input
            label="Full name"
            required
            value={form.full_name}
            onChange={(event) => setForm((c) => ({ ...c, full_name: event.target.value }))}
          />
          <Input
            label="Email"
            type="email"
            required
            value={form.email}
            onChange={(event) => setForm((c) => ({ ...c, email: event.target.value }))}
          />
          <Input
            label="Temporary password"
            type="password"
            required
            hint="At least 10 characters with upper and lowercase, a digit and a symbol."
            value={form.password}
            onChange={(event) => setForm((c) => ({ ...c, password: event.target.value }))}
          />
          <Select
            label="Role"
            value={form.role}
            onChange={(event) =>
              setForm((c) => ({ ...c, role: event.target.value as RoleName }))
            }
          >
            {Object.entries(ROLE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </Select>
          {["STUDENT", "ACADEMICIAN", "INSTITUTION_ADMIN"].includes(form.role) && (
            <Select
              label="Institution"
              value={form.institution_id}
              onChange={(event) =>
                setForm((c) => ({ ...c, institution_id: event.target.value }))
              }
            >
              <option value="">None</option>
              {institutions.data?.data.map((institution) => (
                <option key={institution.id} value={institution.id}>
                  {institution.name}
                </option>
              ))}
            </Select>
          )}
        </div>
      </Dialog>
    </>
  );
}
