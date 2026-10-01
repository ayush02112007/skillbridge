"use client";

import { Compass } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { OpportunityBrowser } from "@/features/shared/opportunity-browser";
import { useAuth } from "@/lib/auth";
import { APP_NAME } from "@/lib/constants";

export function PublicOpportunityBrowser() {
  const { isAuthenticated, session } = useAuth();

  return (
    <div className="min-h-dvh bg-surface-muted">
      <header className="border-b border-ink-200 bg-surface">
        <div className="container flex h-16 items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-lg bg-brand-700 text-white">
              <Compass className="size-4" aria-hidden />
            </span>
            <span className="text-[17px] font-semibold tracking-tight text-ink-950">
              {APP_NAME}
            </span>
          </Link>
          <div className="flex gap-2">
            {isAuthenticated && session ? (
              <Link href={session.home_route}>
                <Button size="sm">Go to dashboard</Button>
              </Link>
            ) : (
              <>
                <Link href="/login">
                  <Button variant="ghost" size="sm">Sign in</Button>
                </Link>
                <Link href="/register">
                  <Button size="sm">Get started</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main id="main" className="container py-8">
        <div className="mb-6">
          <h1>Explore opportunities</h1>
          <p className="mt-1.5 max-w-2xl text-pretty text-sm leading-relaxed text-ink-500">
            Internships, graduate roles and live industry projects.{" "}
            {!isAuthenticated && (
              <>
                <Link href="/register" className="font-medium text-brand-700 hover:underline">
                  Create an account
                </Link>{" "}
                to see how well each one matches your skills, and what you would
                need to close first.
              </>
            )}
          </p>
        </div>

        <OpportunityBrowser
          config={{
            endpoint: "/opportunities",
            emptyTitle: "No opportunities published yet",
            emptyDescription:
              "Postings from partner companies will appear here as soon as they are published.",
          }}
        />
      </main>
    </div>
  );
}
