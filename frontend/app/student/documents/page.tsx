import type { Metadata } from "next";

import { StudentDocuments } from "@/features/student/documents";

export const metadata: Metadata = { title: "Documents" };

export default function Page() {
  return <StudentDocuments />;
}
