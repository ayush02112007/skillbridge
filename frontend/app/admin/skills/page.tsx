import type { Metadata } from "next";

import { AdminTaxonomy } from "@/features/admin/taxonomy";

export const metadata: Metadata = { title: "Skills & Roles" };

export default function Page() {
  return <AdminTaxonomy />;
}
