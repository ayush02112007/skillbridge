"use client";

/**
 * Theme control.
 *
 * Three states, not two: `light`, `dark`, and `system` — which follows the
 * operating system and keeps following it, so a user who switches their laptop
 * to dark at sunset sees the app follow without touching anything.
 *
 * The *applied* class is set by an inline script in the document head before
 * first paint (see `ThemeScript`), so there is no flash of the wrong theme.
 * This provider adopts whatever that script decided rather than re-deciding it.
 */
import {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
} from "react";

export type Theme = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "sb.theme";

interface ThemeContextValue {
  /** What the user chose, including "system". */
  theme: Theme;
  /** What is actually on screen right now. */
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
  /** Light ⇄ dark. From "system", flips away from whatever is showing. */
  toggleTheme: () => void;
  /** False until the client has mounted; guards SSR/first-paint mismatches. */
  isReady: boolean;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function systemTheme(): ResolvedTheme {
  if (typeof window === "undefined" || !window.matchMedia) return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function readStoredTheme(): Theme {
  if (typeof window === "undefined") return "system";
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") return stored;
  } catch {
    // Private mode, or storage blocked. Fall through to the system preference.
  }
  return "system";
}

/**
 * Applies the theme to <html>.
 *
 * `theme-switching` suppresses the colour transition for one frame. Without it
 * the very first application animates, which looks like a bug rather than a
 * flourish.
 */
function applyTheme(resolved: ResolvedTheme, animate: boolean) {
  const root = document.documentElement;
  if (!animate) document.body?.classList.add("theme-switching");
  root.classList.toggle("dark", resolved === "dark");
  root.style.colorScheme = resolved;
  root.dataset.theme = resolved;
  if (!animate) {
    window.requestAnimationFrame(() =>
      document.body?.classList.remove("theme-switching"),
    );
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("system");
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>("light");
  const [isReady, setReady] = useState(false);

  // Adopt what the inline script already applied; do not re-decide and repaint.
  useEffect(() => {
    const stored = readStoredTheme();
    const resolved = stored === "system" ? systemTheme() : stored;
    setThemeState(stored);
    setResolvedTheme(resolved);
    applyTheme(resolved, false);
    setReady(true);
  }, []);

  // Only while the choice is "system": follow the OS as it changes.
  useEffect(() => {
    if (theme !== "system" || typeof window === "undefined" || !window.matchMedia) {
      return;
    }
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (event: MediaQueryListEvent) => {
      const resolved: ResolvedTheme = event.matches ? "dark" : "light";
      setResolvedTheme(resolved);
      applyTheme(resolved, true);
    };
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, [theme]);

  const setTheme = useCallback((next: Theme) => {
    const resolved = next === "system" ? systemTheme() : next;
    setThemeState(next);
    setResolvedTheme(resolved);
    applyTheme(resolved, true);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // Storage unavailable: the choice still applies for this page view.
    }
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  }, [resolvedTheme, setTheme]);

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, resolvedTheme, setTheme, toggleTheme, isReady }),
    [theme, resolvedTheme, setTheme, toggleTheme, isReady],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used inside <ThemeProvider>");
  return context;
}

/**
 * The same context, but tolerant of its absence.
 *
 * Styling hooks read their values out of the computed stylesheet, which is the
 * real source of truth; the context only tells them *when* to read again. A
 * design-system primitive that throws when rendered outside the provider —
 * in a test, in isolation, in a story — would be needlessly brittle, so those
 * hooks use this instead.
 */
export function useOptionalTheme(): ThemeContextValue | null {
  return useContext(ThemeContext);
}

/**
 * Runs before first paint, synchronously, in <head>.
 *
 * It duplicates a few lines of the provider's logic on purpose: React has not
 * hydrated at this point, and anything that waits for React is a frame too
 * late — the page would paint light and then snap to dark.
 */
export function ThemeScript() {
  const script = `
(function () {
  try {
    var stored = localStorage.getItem("${THEME_STORAGE_KEY}");
    var resolved =
      stored === "light" || stored === "dark"
        ? stored
        : window.matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light";
    var root = document.documentElement;
    if (resolved === "dark") root.classList.add("dark");
    root.style.colorScheme = resolved;
    root.dataset.theme = resolved;
  } catch (e) {
    /* Storage or matchMedia unavailable: light is the safe default. */
  }
})();`.trim();

  return <script dangerouslySetInnerHTML={{ __html: script }} />;
}
