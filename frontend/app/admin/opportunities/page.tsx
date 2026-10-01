import type { Metadata } from "next";

import { AdminModeration } from "@/features/admin/moderation";

export const metadata: Metadata = { title: "Moderation" };

export default function Page() {
  return <AdminModeration />;
}
