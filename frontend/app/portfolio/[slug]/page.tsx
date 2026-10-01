import type { Metadata } from "next";

import { PublicPortfolioView } from "@/features/portfolio/public-portfolio";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  return {
    title: `Portfolio · ${slug}`,
    description: "A SkillBridge digital portfolio with verified credentials.",
  };
}

export default async function PortfolioPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <PublicPortfolioView slug={slug} />;
}
