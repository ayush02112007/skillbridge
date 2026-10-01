import type { Metadata } from "next";

import { PublicCompanyProfile } from "@/features/opportunities/company-profile";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  return { title: `Company · ${slug}` };
}

export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <PublicCompanyProfile slug={slug} />;
}
