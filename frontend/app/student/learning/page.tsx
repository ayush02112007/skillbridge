import type { Metadata } from "next";
import { Suspense } from "react";

import { StudentLearning } from "@/features/student/learning";

export const metadata: Metadata = { title: "Learning Programs" };

export default function LearningPage() {
  return (
    <Suspense>
      <StudentLearning />
    </Suspense>
  );
}
