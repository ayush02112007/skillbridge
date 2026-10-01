import type { Metadata } from "next";

import { InterviewPrep } from "@/features/student/interview-prep";

export const metadata: Metadata = { title: "Interview Preparation" };

export default function Page() {
  return <InterviewPrep />;
}
