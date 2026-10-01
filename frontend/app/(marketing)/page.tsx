import type { Metadata } from "next";

import { LandingPage } from "@/features/marketing/landing-page";

export const metadata: Metadata = {
  title: "Bridge the gap between education and industry",
  description:
    "SkillBridge is an industry-aware employability platform. Assess your " +
    "skills, see exactly what a role requires, follow a learning path that " +
    "closes the gap, and get matched to opportunities you are ready for.",
};

export default function HomePage() {
  return <LandingPage />;
}
