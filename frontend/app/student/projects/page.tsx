import type { Metadata } from "next";

import { PageHeader } from "@/components/layout/page-header";
import { OpportunityBrowser } from "@/features/shared/opportunity-browser";

export const metadata: Metadata = { title: "Live Projects" };

export default function Page() {
  return (
    <>
      <PageHeader title="Live Projects" description="Real problems published by industry for student teams." />
      <OpportunityBrowser
        config={{
          endpoint: "/projects",
          emptyTitle: "No live projects yet",
          emptyDescription: "Industry projects open for student teams will appear here.",
        }}
      />
    </>
  );
}
