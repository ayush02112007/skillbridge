import type { Metadata } from "next";

import { OpportunityDetailView } from "@/features/opportunities/detail";

export const metadata: Metadata = { title: "Opportunity" };

export default async function OpportunityPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <OpportunityDetailView opportunityId={id} />;
}
