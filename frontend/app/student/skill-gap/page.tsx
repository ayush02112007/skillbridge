import type { Metadata } from "next";

import { SkillGapAnalysis } from "@/features/student/skill-gap";

export const metadata: Metadata = { title: "Skill Gap" };

export default function SkillGapPage() {
  return <SkillGapAnalysis />;
}
