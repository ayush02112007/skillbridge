import type { Metadata } from "next";

import { AdminDashboard } from "@/features/admin/dashboard";

export const metadata: Metadata = { title: "Platform Dashboard" };

export default function Page() {
  return <AdminDashboard />;
}
