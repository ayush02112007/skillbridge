import { Compass } from "lucide-react";
import Link from "next/link";

import { ThemeToggle } from "@/components/ui/theme-toggle";
import { APP_NAME, APP_TAGLINE } from "@/lib/constants";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      {/* Form side */}
      <div className="flex flex-col">
        <header className="flex items-center justify-between p-6">
          <Link href="/" className="inline-flex items-center gap-2.5" aria-label={`${APP_NAME} home`}>
            <span className="flex size-8 items-center justify-center rounded-lg bg-brand-700 text-white">
              <Compass className="size-4" aria-hidden />
            </span>
            <span className="text-[17px] font-semibold tracking-tight text-ink-950">
              {APP_NAME}
            </span>
          </Link>
          <ThemeToggle />
        </header>
        <main id="main" className="flex flex-1 items-center justify-center px-6 pb-10">
          <div className="w-full max-w-sm">{children}</div>
        </main>
      </div>

      {/* Context side: hidden on small screens where it would only add scroll. */}
      <aside className="relative hidden overflow-hidden bg-canvas lg:block">
        <div className="hero-grid absolute inset-0 opacity-[0.15]" aria-hidden />
        <div className="relative flex h-full flex-col justify-center p-12 text-white">
          <blockquote className="max-w-md">
            <p className="text-balance text-3xl font-semibold leading-tight tracking-[-0.02em]">
              {APP_TAGLINE}
            </p>
            <p className="mt-5 text-pretty leading-relaxed text-ink-300">
              Assess what you can do, see precisely what a role expects, and
              follow a path that closes the difference. Every recommendation
              explains itself.
            </p>
          </blockquote>

          <dl className="mt-12 grid max-w-md grid-cols-2 gap-6">
            {[
              ["Measured, not claimed", "Skills carry the evidence behind them"],
              ["Explainable matching", "Every score shows its working"],
              ["Verified experience", "Placements write back to your portfolio"],
              ["Privacy by default", "Documents are private until you share them"],
            ].map(([title, body]) => (
              <div key={title}>
                <dt className="text-sm font-semibold text-white">{title}</dt>
                <dd className="mt-1 text-sm leading-relaxed text-ink-400">{body}</dd>
              </div>
            ))}
          </dl>
        </div>
      </aside>
    </div>
  );
}
