import type { Metadata } from "next";

import { ResearchPage } from "@/features/shared/research-page";

export const metadata: Metadata = { title: "Research & Consultancy" };

export default function Page() {
  return <ResearchPage mode="academician" />;
}
