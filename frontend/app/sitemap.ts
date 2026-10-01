import type { MetadataRoute } from "next";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: siteUrl, lastModified: now, changeFrequency: "weekly", priority: 1 },
    { url: `${siteUrl}/opportunities`, lastModified: now, changeFrequency: "daily", priority: 0.9 },
    { url: `${siteUrl}/login`, lastModified: now, changeFrequency: "monthly", priority: 0.4 },
    { url: `${siteUrl}/register`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
  ];
}
