import type { Metadata } from "next";

import { StudentProfileEditor } from "@/features/student/profile";

export const metadata: Metadata = { title: "My Profile" };

export default function Page() {
  return <StudentProfileEditor />;
}
