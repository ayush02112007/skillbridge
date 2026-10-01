import { cn } from "@/lib/utils";

export function Card({
  className,
  interactive,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { interactive?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-ink-200/80 bg-surface shadow-card",
        interactive &&
          "transition-all hover:-translate-y-0.5 hover:border-ink-300 hover:shadow-lifted",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-1 p-5 pb-3", className)} {...props} />;
}

/**
 * A card is normally a top-level section of its page, so its title sits
 * directly under the page <h1> and `h2` is the correct level. Pages that
 * group cards under their own heading pass `as="h3"` to keep the outline
 * honest.
 */
export function CardTitle({
  as: Tag = "h2",
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement> & { as?: "h2" | "h3" | "h4" }) {
  return (
    <Tag
      className={cn("text-[15px] font-semibold leading-tight text-ink-900", className)}
      {...props}
    />
  );
}

export function CardDescription({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm leading-relaxed text-ink-500", className)} {...props} />;
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5 pt-0", className)} {...props} />;
}

export function CardFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("flex items-center gap-2 border-t border-ink-100 p-5 py-3", className)}
      {...props}
    />
  );
}
