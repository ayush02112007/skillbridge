import type { Metadata } from "next";

import { PlacementsView } from "@/features/institution/directory";

export const metadata: Metadata = { title: "Placements" };

export default function Page() {
  return <PlacementsView mode="placement" />;
}
