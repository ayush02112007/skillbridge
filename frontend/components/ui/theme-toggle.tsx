"use client";

/**
 * Light / dark control.
 *
 * Two shapes from one piece of logic:
 *   `<ThemeToggle />`      a single button — one click, light ⇄ dark
 *   `<ThemeToggle menu />` a three-way segmented control including "System"
 *
 * The icon is the *current* theme, and the accessible name says what the click
 * will do, because a sun that means "you are in light mode" and a sun that
 * means "switch to light mode" are indistinguishable without it.
 */
import { Monitor, Moon, Sun } from "lucide-react";

import { useTheme, type Theme } from "@/lib/theme";
import { cn } from "@/lib/utils";

const OPTIONS: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

export function ThemeToggle({
  menu = false,
  className,
  size = "md",
}: {
  menu?: boolean;
  className?: string;
  size?: "sm" | "md";
}) {
  const { theme, resolvedTheme, setTheme, toggleTheme, isReady } = useTheme();

  if (menu) {
    return (
      <div
        role="radiogroup"
        aria-label="Colour theme"
        className={cn(
          "inline-flex items-center gap-0.5 rounded-lg border border-ink-200 bg-surface-muted p-0.5",
          className,
        )}
      >
        {OPTIONS.map((option) => {
          const Icon = option.icon;
          const selected = theme === option.value;
          return (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => setTheme(option.value)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium",
                "transition-colors focus-visible:outline-none focus-visible:ring-2",
                "focus-visible:ring-brand-600",
                selected
                  ? "bg-surface text-ink-900 shadow-card"
                  : "text-ink-500 hover:text-ink-800",
              )}
            >
              <Icon className="size-3.5" aria-hidden />
              {option.label}
            </button>
          );
        })}
      </div>
    );
  }

  const nextLabel = resolvedTheme === "dark" ? "light" : "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      // Until the client has mounted, the server-rendered markup cannot know
      // which theme is showing; hiding it from AT for that instant is better
      // than announcing the wrong one.
      aria-hidden={!isReady || undefined}
      aria-label={`Switch to ${nextLabel} theme`}
      title={`Switch to ${nextLabel} theme`}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-lg text-ink-500",
        "transition-colors hover:bg-ink-100 hover:text-ink-800",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600",
        size === "sm" ? "size-8" : "size-9",
        className,
      )}
    >
      {/*
        Both glyphs are rendered and one is hidden by the theme, so the swap is
        a CSS change with no layout shift and nothing to re-mount.
      */}
      <Sun
        className={cn("animate-theme-in", size === "sm" ? "size-4" : "size-[18px]", "dark:hidden")}
        aria-hidden
      />
      <Moon
        className={cn("hidden animate-theme-in", size === "sm" ? "size-4" : "size-[18px]", "dark:block")}
        aria-hidden
      />
    </button>
  );
}
