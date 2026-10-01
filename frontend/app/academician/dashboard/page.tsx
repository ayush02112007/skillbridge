import type { Metadata } from "next";

import { AcademicianDashboard } from "@/features/academician/dashboard";

export const metadata: Metadata = { title: "Academician Dashboard" };

export default function Page() {
  return <AcademicianDashboard />;
}
