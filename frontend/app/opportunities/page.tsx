import type { Metadata } from "next";

import { PublicOpportunityBrowser } from "@/features/opportunities/public-browser";

export const metadata: Metadata = {
  title: "Explore opportunities",
  description:
    "Browse internships, jobs and live industry projects on SkillBridge. " +
    "Sign in to see how well each one matches your skills.",
};

export default function OpportunitiesPage() {
  return <PublicOpportunityBrowser />;
}
