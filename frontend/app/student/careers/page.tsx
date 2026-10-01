import type { Metadata } from "next";

import { CareerRecommendations } from "@/features/student/careers";

export const metadata: Metadata = { title: "Career Recommendations" };

export default function Page() {
  return <CareerRecommendations />;
}
