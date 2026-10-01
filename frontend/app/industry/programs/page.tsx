import type { Metadata } from "next";

import { IndustryPrograms } from "@/features/industry/programs";

export const metadata: Metadata = { title: "Learning Programmes" };

export default function Page() {
  return <IndustryPrograms />;
}
