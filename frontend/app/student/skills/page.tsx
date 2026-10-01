import type { Metadata } from "next";

import { SkillsManager } from "@/features/student/skills-manager";

export const metadata: Metadata = { title: "My Skills" };

export default function StudentSkillsPage() {
  return <SkillsManager />;
}
