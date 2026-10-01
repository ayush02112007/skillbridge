import type { MetadataRoute } from "next";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/opportunities", "/portfolio"],
        // Authenticated areas hold personal data and must never be indexed.
        disallow: [
          "/student/", "/industry/", "/institution/", "/academician/", "/admin/",
          "/api/",
        ],
      },
    ],
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}
