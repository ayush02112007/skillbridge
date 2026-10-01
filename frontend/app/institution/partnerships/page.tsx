import type { Metadata } from "next";

import { Partnerships } from "@/features/institution/directory";

export const metadata: Metadata = { title: "Industry Partners" };

export default function Page() {
  return <Partnerships />;
}
