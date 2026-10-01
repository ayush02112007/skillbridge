import type { Metadata } from "next";

import { MentorshipPanel } from "@/features/shared/mentorship-panel";

export const metadata: Metadata = { title: "Mentorship" };

export default function Page() {
  return <MentorshipPanel role="mentor" />;
}
