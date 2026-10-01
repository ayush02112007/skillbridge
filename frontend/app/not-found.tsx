import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main
      id="main"
      className="flex min-h-dvh flex-col items-center justify-center gap-4 px-6 text-center"
    >
      <p className="font-mono text-sm text-ink-400">404</p>
      <h1 className="text-2xl font-semibold text-ink-900">This page does not exist</h1>
      <p className="max-w-md text-sm text-ink-500">
        The link may be out of date, or the item may have been closed or removed.
      </p>
      <div className="mt-2 flex gap-2">
        <Link href="/">
          <Button variant="secondary">Back to home</Button>
        </Link>
        <Link href="/opportunities">
          <Button>Explore opportunities</Button>
        </Link>
      </div>
    </main>
  );
}
