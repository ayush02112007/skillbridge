"use client";

import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Skeleton block. Used instead of spinners so layout does not jump. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-ink-100", className)}
      aria-hidden
    />
  );
}

export function SkeletonCard({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3 rounded-2xl border border-ink-200/80 bg-surface p-5 shadow-card">
      <Skeleton className="h-4 w-1/3" />
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className={cn("h-3", index % 2 ? "w-full" : "w-4/5")} />
      ))}
    </div>
  );
}

export function SkeletonList({ count = 3, rows = 3 }: { count?: number; rows?: number }) {
  return (
    <div className="grid gap-4" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading</span>
      {Array.from({ length: count }).map((_, index) => (
        <SkeletonCard key={index} rows={rows} />
      ))}
    </div>
  );
}

export function SkeletonStats({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-busy="true">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="space-y-3 rounded-2xl border border-ink-200/80 bg-surface p-5 shadow-card"
        >
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-7 w-16" />
          <Skeleton className="h-2 w-full" />
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-2xl border border-dashed " +
          "border-ink-200 bg-surface-muted/60 px-6 py-12 text-center",
        className,
      )}
    >
      <div className="mb-3 flex size-11 items-center justify-center rounded-full bg-surface text-ink-400 shadow-card [&_svg]:size-5">
        {icon ?? <Inbox />}
      </div>
      <p className="text-sm font-semibold text-ink-800">{title}</p>
      {description && (
        <p className="mt-1 max-w-sm text-sm leading-relaxed text-ink-500">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
  className,
}: {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}) {
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : "Something went wrong.";
  const code = error instanceof ApiError ? error.code : undefined;

  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center justify-center rounded-2xl border border-danger-500/20 " +
          "bg-danger-50/60 px-6 py-10 text-center",
        className,
      )}
    >
      <div className="mb-3 flex size-11 items-center justify-center rounded-full bg-surface text-danger-600 shadow-card [&_svg]:size-5">
        <AlertTriangle />
      </div>
      <p className="text-sm font-semibold text-ink-900">We could not load this</p>
      <p className="mt-1 max-w-sm text-sm text-ink-600">{message}</p>
      {code && <p className="mt-1 font-mono text-2xs text-ink-400">{code}</p>}
      {onRetry && (
        <Button
          variant="secondary"
          size="sm"
          className="mt-4"
          onClick={onRetry}
          leftIcon={<RefreshCw />}
        >
          Try again
        </Button>
      )}
    </div>
  );
}

/**
 * One component to handle the four states every data view needs.
 * Using it everywhere is what stops blank screens appearing.
 */
export function QueryState<T>({
  isLoading,
  error,
  data,
  onRetry,
  loading,
  empty,
  isEmpty,
  children,
}: {
  isLoading: boolean;
  error: unknown;
  data: T | undefined;
  onRetry?: () => void;
  loading?: React.ReactNode;
  empty?: React.ReactNode;
  isEmpty?: (data: T) => boolean;
  children: (data: T) => React.ReactNode;
}) {
  if (isLoading) return <>{loading ?? <SkeletonList />}</>;
  if (error) return <ErrorState error={error} onRetry={onRetry} />;
  if (data === undefined || data === null) {
    return <>{empty ?? <EmptyState title="Nothing to show yet" />}</>;
  }
  if (isEmpty?.(data)) {
    return <>{empty ?? <EmptyState title="Nothing to show yet" />}</>;
  }
  return <>{children(data)}</>;
}
