import { cn } from "@/lib/utils";

/**
 * Responsive table. On small screens the wrapper scrolls horizontally and stays
 * keyboard reachable, which keeps data tables usable rather than clipped.
 */
export function TableWrapper({
  children,
  className,
  caption,
}: {
  children: React.ReactNode;
  className?: string;
  caption?: string;
}) {
  return (
    <div
      className={cn(
        "overflow-x-auto rounded-2xl border border-ink-200/80 bg-surface shadow-card",
        className,
      )}
      tabIndex={0}
      role="region"
      aria-label={caption ?? "Data table"}
    >
      {children}
    </div>
  );
}

export function Table({ className, ...props }: React.TableHTMLAttributes<HTMLTableElement>) {
  return <table className={cn("w-full border-collapse text-sm", className)} {...props} />;
}

export function THead({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead
      className={cn("border-b border-ink-200 bg-surface-muted text-left", className)}
      {...props}
    />
  );
}

export function TH({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope="col"
      className={cn(
        "whitespace-nowrap px-4 py-2.5 text-2xs font-semibold uppercase tracking-wide text-ink-500",
        className,
      )}
      {...props}
    />
  );
}

export function TBody({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn("divide-y divide-ink-100", className)} {...props} />;
}

export function TR({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn("transition-colors hover:bg-surface-muted/60", className)} {...props} />;
}

export function TD({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("px-4 py-3 align-middle text-ink-700", className)} {...props} />;
}
