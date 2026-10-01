import type { Metadata } from "next";

import { AdminDashboard } from "@/features/admin/dashboard";

export const metadata: Metadata = { title: "Platform Analytics" };

export default function Page() {
  return <AdminDashboard />;
}
