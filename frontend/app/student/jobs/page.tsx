import type { Metadata } from "next";

import { PageHeader } from "@/components/layout/page-header";
import { OpportunityBrowser } from "@/features/shared/opportunity-browser";

export const metadata: Metadata = { title: "Jobs" };

export default function Page() {
  return (
    <>
      <PageHeader title="Jobs" description="Graduate and entry-level roles, ranked by how well your evidenced skills fit." />
      <OpportunityBrowser
        config={{
          endpoint: "/jobs",
          emptyTitle: "No jobs available yet",
          emptyDescription: "Job postings from partner companies will appear here.",
        }}
      />
    </>
  );
}
