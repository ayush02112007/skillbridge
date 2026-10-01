import type { Metadata } from "next";

import { AcademicianProfileEditor } from "@/features/academician/profile";

export const metadata: Metadata = { title: "My Profile" };

export default function Page() {
  return <AcademicianProfileEditor />;
}
