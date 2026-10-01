import type { Metadata } from "next";

import { InstitutionReports } from "@/features/institution/reports";

export const metadata: Metadata = { title: "Reports" };

export default function Page() {
  return <InstitutionReports />;
}
