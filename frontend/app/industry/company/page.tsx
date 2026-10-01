import type { Metadata } from "next";

import { CompanyProfile } from "@/features/industry/company-profile";

export const metadata: Metadata = { title: "Company Profile" };

export default function Page() {
  return <CompanyProfile />;
}
