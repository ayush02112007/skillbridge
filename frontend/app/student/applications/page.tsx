import type { Metadata } from "next";
import { Suspense } from "react";

import { StudentApplications } from "@/features/student/applications";

export const metadata: Metadata = { title: "Applications" };

export default function ApplicationsPage() {
  return (
    <Suspense>
      <StudentApplications />
    </Suspense>
  );
}
