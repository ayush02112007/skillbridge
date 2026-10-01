"use client";

import { RefreshCw } from "lucide-react";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surfaced to the browser console; a production deployment would forward
    // this to the configured error-monitoring service.
    console.error("Unhandled UI error", error);
  }, [error]);

  return (
    <main
      id="main"
      className="flex min-h-dvh flex-col items-center justify-center gap-4 px-6 text-center"
    >
      <h1 className="text-2xl font-semibold text-ink-900">Something went wrong</h1>
      <p className="max-w-md text-sm text-ink-500">
        The page failed to render. Retrying often resolves it; if it persists,
        the reference below helps support trace it.
      </p>
      {error.digest && (
        <p className="font-mono text-2xs text-ink-400">Reference: {error.digest}</p>
      )}
      <Button className="mt-2" onClick={reset} leftIcon={<RefreshCw />}>
        Try again
      </Button>
    </main>
  );
}
