import type { Metadata } from "next";

import { AdminSystem } from "@/features/admin/system";

export const metadata: Metadata = { title: "System Health" };

export default function Page() {
  return <AdminSystem />;
}
