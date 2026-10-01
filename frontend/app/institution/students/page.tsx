import type { Metadata } from "next";

import { InstitutionStudents } from "@/features/institution/students";

export const metadata: Metadata = { title: "Students" };

export default function Page() {
  return <InstitutionStudents />;
}
