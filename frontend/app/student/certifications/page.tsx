import type { Metadata } from "next";

import { StudentCertifications } from "@/features/student/certifications";

export const metadata: Metadata = { title: "Certifications" };

export default function Page() {
  return <StudentCertifications />;
}
