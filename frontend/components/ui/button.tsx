"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { forwardRef } from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg font-medium " +
    "transition-colors focus-visible:outline-none focus-visible:ring-2 " +
    "focus-visible:ring-brand-600 focus-visible:ring-offset-2 " +
    "disabled:pointer-events-none disabled:opacity-50 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-fg shadow-sm hover:bg-primary-hover active:bg-primary-active",
        secondary:
          "bg-surface text-ink-800 border border-ink-200 shadow-sm hover:bg-ink-50 active:bg-ink-100",
        ghost: "text-ink-700 hover:bg-ink-100 active:bg-ink-200",
        subtle: "bg-brand-50 text-brand-800 hover:bg-brand-100",
        danger: "bg-danger-solid text-primary-fg shadow-sm hover:bg-danger-solid-hover",
        success: "bg-success-solid text-primary-fg shadow-sm hover:bg-success-solid-hover",
        link: "text-brand-700 underline-offset-4 hover:underline p-0 h-auto",
      },
      size: {
        sm: "h-8 px-3 text-sm [&_svg]:size-4",
        md: "h-10 px-4 text-sm [&_svg]:size-4",
        lg: "h-11 px-5 text-base [&_svg]:size-5",
        icon: "h-9 w-9 [&_svg]:size-4",
      },
      block: { true: "w-full" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { className, variant, size, block, isLoading, leftIcon, rightIcon, children, disabled, ...props },
    ref,
  ) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size, block }), className)}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      {...props}
    >
      {isLoading ? <Loader2 className="animate-spin" aria-hidden /> : leftIcon}
      {children}
      {!isLoading && rightIcon}
    </button>
  ),
);
Button.displayName = "Button";

export { buttonVariants };
