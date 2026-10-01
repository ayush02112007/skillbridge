import type { Metadata } from "next";
import { Suspense } from "react";

import { IndustryApplicants } from "@/features/industry/applicants";

export const metadata: Metadata = { title: "Applicants" };

export default function Page() {
  return (
    <Suspense>
      <IndustryApplicants />
    </Suspense>
  );
}
