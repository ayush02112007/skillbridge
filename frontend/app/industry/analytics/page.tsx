import type { Metadata } from "next";

import { IndustryDashboard } from "@/features/industry/dashboard";

export const metadata: Metadata = { title: "Analytics" };

export default function Page() {
  return <IndustryDashboard />;
}
