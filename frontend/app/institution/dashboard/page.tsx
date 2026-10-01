import type { Metadata } from "next";

import { InstitutionDashboard } from "@/features/institution/dashboard";

export const metadata: Metadata = { title: "Institution Dashboard" };

export default function Page() {
  return <InstitutionDashboard />;
}
