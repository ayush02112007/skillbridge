"use client";

import { Toaster } from "sonner";

import { useTheme } from "@/lib/theme";

/**
 * Sonner renders outside the app's styling, so it needs the theme handed to it
 * explicitly — otherwise toasts stay light on a dark page.
 */
export function ThemedToaster() {
  const { resolvedTheme } = useTheme();
  return (
    <Toaster
      position="top-right"
      theme={resolvedTheme}
      richColors
      closeButton
      toastOptions={{ className: "text-sm" }}
    />
  );
}
