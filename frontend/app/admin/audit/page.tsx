import type { Metadata } from "next";

import { AdminAudit } from "@/features/admin/audit";

export const metadata: Metadata = { title: "Audit Log" };

export default function Page() {
  return <AdminAudit />;
}
