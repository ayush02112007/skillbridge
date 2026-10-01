import { cn, initials } from "@/lib/utils";

const SIZES = {
  xs: "size-6 text-2xs",
  sm: "size-8 text-xs",
  md: "size-10 text-sm",
  lg: "size-14 text-base",
  xl: "size-20 text-xl",
};

export function Avatar({
  name,
  src,
  size = "md",
  className,
}: {
  name?: string | null;
  src?: string | null;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  const label = name ?? "User";
  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt={label}
        className={cn("shrink-0 rounded-full border border-ink-200 object-cover", SIZES[size], className)}
      />
    );
  }
  return (
    <span
      aria-hidden
      title={label}
      className={cn(
        "inline-flex shrink-0 select-none items-center justify-center rounded-full " +
          "bg-brand-100 font-semibold text-brand-800",
        SIZES[size],
        className,
      )}
    >
      {initials(name)}
    </span>
  );
}
