import type { Metadata } from "next";

import { PostingManager } from "@/features/industry/posting-manager";

export const metadata: Metadata = { title: "Live Projects" };

export default function Page() {
  return (
    <PostingManager
      config={{
        kind: "project",
        endpoint: "/projects",
        title: "Live projects",
        description:
          "Real problems published for student teams, with milestones and evaluation.",
      }}
    />
  );
}
