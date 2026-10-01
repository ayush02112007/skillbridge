import type { Metadata } from "next";

import { AdminAssessments } from "@/features/admin/moderation";

export const metadata: Metadata = { title: "Assessments" };

export default function Page() {
  return <AdminAssessments />;
}
