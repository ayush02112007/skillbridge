import type { Metadata } from "next";

import { PostingManager } from "@/features/industry/posting-manager";

export const metadata: Metadata = { title: "Internships" };

export default function Page() {
  return (
    <PostingManager
      config={{
        kind: "internship",
        endpoint: "/internships",
        title: "Internships",
        description:
          "Your internship postings, their reach and the applicants they attract.",
      }}
    />
  );
}
