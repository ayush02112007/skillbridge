import type { Metadata, Viewport } from "next";

import { ThemedToaster } from "@/components/layout/themed-toaster";
import { AuthProvider } from "@/lib/auth";
import { APP_NAME, APP_SUBTITLE, APP_TAGLINE } from "@/lib/constants";
import { QueryProvider } from "@/lib/query";
import { ThemeProvider, ThemeScript } from "@/lib/theme";

import "./globals.css";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: `${APP_NAME} — ${APP_SUBTITLE}`,
    template: `%s · ${APP_NAME}`,
  },
  description:
    "SkillBridge connects students, academicians, institutions and industry. " +
    "Assess your skills, see exactly what a role requires, follow a learning " +
    "path that closes the gap, and get matched to real opportunities.",
  keywords: [
    "employability", "skill gap analysis", "campus placements", "internships",
    "industry academia collaboration", "career readiness",
  ],
  authors: [{ name: "SkillBridge" }],
  openGraph: {
    type: "website",
    siteName: APP_NAME,
    title: `${APP_NAME} — ${APP_TAGLINE}`,
    description:
      "An industry-aware employability platform: assess skills, close the gap, " +
      "and reach the opportunities you are actually ready for.",
    url: siteUrl,
  },
  twitter: {
    card: "summary_large_image",
    title: `${APP_NAME} — ${APP_TAGLINE}`,
    description: "Assess skills, close the gap, reach real opportunities.",
  },
  robots: { index: true, follow: true },
  icons: { icon: "/icon.svg", shortcut: "/icon.svg", apple: "/icon.svg" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // The browser chrome (mobile address bar, PWA surfaces) follows the theme.
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f7f8fa" },
    { media: "(prefers-color-scheme: dark)", color: "#0d1117" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // suppressHydrationWarning: ThemeScript adds the `dark` class to <html>
    // before React hydrates, so the client tree legitimately differs here.
    <html lang="en" suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body className="min-h-dvh">
        <a href="#main" className="skip-link">
          Skip to main content
        </a>
        <ThemeProvider>
          <QueryProvider>
            <AuthProvider>
              {children}
              <ThemedToaster />
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
