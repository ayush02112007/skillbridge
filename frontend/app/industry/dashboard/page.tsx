import type { Metadata } from "next";

import { IndustryDashboard } from "@/features/industry/dashboard";

export const metadata: Metadata = { title: "Industry Dashboard" };

export default function Page() {
  return <IndustryDashboard />;
}
