import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border font-medium whitespace-nowrap",
  {
    variants: {
      tone: {
        neutral: "border-ink-200 bg-ink-50 text-ink-700",
        brand: "border-brand-200 bg-brand-50 text-brand-800",
        success: "border-success-500/25 bg-success-50 text-success-700",
        warning: "border-warning-500/25 bg-warning-50 text-warning-600",
        danger: "border-danger-500/25 bg-danger-50 text-danger-700",
        accent: "border-accent-300/50 bg-accent-50 text-accent-800",
        outline: "border-ink-300 bg-transparent text-ink-600",
      },
      size: {
        sm: "px-2 py-0.5 text-2xs [&_svg]:size-3",
        md: "px-2.5 py-1 text-xs [&_svg]:size-3.5",
      },
    },
    defaultVariants: { tone: "neutral", size: "sm" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, size, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone, size }), className)} {...props} />;
}
