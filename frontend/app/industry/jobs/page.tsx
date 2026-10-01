import type { Metadata } from "next";

import { PostingManager } from "@/features/industry/posting-manager";

export const metadata: Metadata = { title: "Jobs" };

export default function Page() {
  return (
    <PostingManager
      config={{
        kind: "job",
        endpoint: "/jobs",
        title: "Jobs",
        description:
          "Your job postings, their reach and the applicants they attract.",
      }}
    />
  );
}
