import type { Metadata } from "next";

import { FacultyOpportunities } from "@/features/academician/faculty-opportunities";

export const metadata: Metadata = { title: "Faculty Programmes" };

export default function Page() {
  return <FacultyOpportunities />;
}
