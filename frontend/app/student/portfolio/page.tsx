import type { Metadata } from "next";

import { PortfolioSettings } from "@/features/student/portfolio-settings";

export const metadata: Metadata = { title: "Digital Portfolio" };

export default function Page() {
  return <PortfolioSettings />;
}
