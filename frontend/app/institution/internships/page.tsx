import type { Metadata } from "next";

import { PlacementsView } from "@/features/institution/directory";

export const metadata: Metadata = { title: "Internships" };

export default function Page() {
  return <PlacementsView mode="internship" />;
}
