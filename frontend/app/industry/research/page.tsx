import type { Metadata } from "next";

import { ResearchPage } from "@/features/shared/research-page";

export const metadata: Metadata = { title: "Research" };

export default function Page() {
  return <ResearchPage mode="industry" />;
}
