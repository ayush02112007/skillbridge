import type { Metadata } from "next";

import { Assessments } from "@/features/student/assessments";

export const metadata: Metadata = { title: "Skill Assessment" };

export default function AssessmentPage() {
  return <Assessments />;
}
