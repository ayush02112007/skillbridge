import type { Metadata } from "next";

import { InstitutionDashboard } from "@/features/institution/dashboard";

export const metadata: Metadata = { title: "Analytics" };

export default function Page() {
  return <InstitutionDashboard />;
}
