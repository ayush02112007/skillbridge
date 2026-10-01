import type { Metadata } from "next";

import { PageHeader } from "@/components/layout/page-header";
import { OpportunityBrowser } from "@/features/shared/opportunity-browser";

export const metadata: Metadata = { title: "Internships" };

export default function Page() {
  return (
    <>
      <PageHeader title="Internships" description="Internships matched to your skills. Sort by fit to see where you are strongest." />
      <OpportunityBrowser
        config={{
          endpoint: "/internships",
          emptyTitle: "No internships available yet",
          emptyDescription: "Internships posted by partner companies will appear here.",
        }}
      />
    </>
  );
}
