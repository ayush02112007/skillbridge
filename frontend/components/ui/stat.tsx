import { ArrowDownRight, ArrowUpRight } from "lucide-react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function Stat({
  label,
  value,
  sublabel,
  icon,
  trend,
  tone = "brand",
  className,
}: {
  label: string;
  value: React.ReactNode;
  sublabel?: string;
  icon?: React.ReactNode;
  trend?: { value: number; label?: string };
  tone?: "brand" | "success" | "warning" | "danger" | "accent" | "ink";
  className?: string;
}) {
  const toneClass = {
    brand: "bg-brand-50 text-brand-700",
    success: "bg-success-50 text-success-700",
    warning: "bg-warning-50 text-warning-600",
    danger: "bg-danger-50 text-danger-600",
    accent: "bg-accent-50 text-accent-700",
    ink: "bg-ink-100 text-ink-600",
  }[tone];

  return (
    <Card className={cn("p-5", className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-500">{label}</p>
          <p className="text-2xl font-semibold tabular-nums leading-none text-ink-900">
            {value}
          </p>
          {sublabel && <p className="truncate text-xs text-ink-500">{sublabel}</p>}
        </div>
        {icon && (
          <span
            className={cn("flex size-9 shrink-0 items-center justify-center rounded-xl [&_svg]:size-4", toneClass)}
            aria-hidden
          >
            {icon}
          </span>
        )}
      </div>
      {trend && (
        <p
          className={cn(
            "mt-3 inline-flex items-center gap-1 text-xs font-medium",
            trend.value >= 0 ? "text-success-700" : "text-danger-600",
          )}
        >
          {trend.value >= 0 ? (
            <ArrowUpRight className="size-3.5" />
          ) : (
            <ArrowDownRight className="size-3.5" />
          )}
          {Math.abs(trend.value)}%{trend.label ? ` ${trend.label}` : ""}
        </p>
      )}
    </Card>
  );
}
