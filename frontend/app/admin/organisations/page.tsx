import type { Metadata } from "next";

import { AdminOrganisations } from "@/features/admin/moderation";

export const metadata: Metadata = { title: "Organisations" };

export default function Page() {
  return <AdminOrganisations />;
}
