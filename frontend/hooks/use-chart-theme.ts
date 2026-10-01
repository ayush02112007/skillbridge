"use client";

/**
 * Chart colours, read from the active theme.
 *
 * Recharts writes its colours as SVG presentation *attributes*, and those do
 * not resolve `var(...)`. So the values are read out of the computed style
 * once per theme change and handed over as concrete strings — which also gives
 * the legend and tooltip swatches the right colour, not just the geometry.
 */
import { useEffect, useState } from "react";

import { useOptionalTheme } from "@/lib/theme";

export interface ChartTheme {
  /** Categorical series palette, ordered so neighbours stay distinguishable. */
  colors: string[];
  /** Cartesian and polar grid lines. */
  grid: string;
  /** Axis lines and ticks. */
  axis: string;
  /** Axis labels and legend text. */
  label: string;
  /** The unfilled remainder of a gauge or progress track. */
  track: string;
  /** Card background, for tooltip and pie-slice borders. */
  surface: string;
}

const LIGHT_FALLBACK: ChartTheme = {
  colors: ["#2469a8", "#17996b", "#ff8312", "#7c5cbf", "#0e7490",
           "#d93a35", "#b45309", "#515c76"],
  grid: "#eceef2",
  axis: "#b0b8c9",
  label: "#66738f",
  track: "#eceef2",
  surface: "#ffffff",
};

function readVar(styles: CSSStyleDeclaration, name: string, fallback: string): string {
  const value = styles.getPropertyValue(name).trim();
  if (!value) return fallback;
  // Neutral tokens are stored as bare RGB channels for Tailwind's alpha
  // composition; the series palette is stored as plain hex.
  return /^[\d\s]+$/.test(value) ? `rgb(${value.split(/\s+/).join(" ")})` : value;
}

export function useChartTheme(): ChartTheme {
  // Optional on purpose: the values come from the stylesheet either way, and a
  // chart should still render outside the provider.
  const theme = useOptionalTheme();
  const resolvedTheme = theme?.resolvedTheme;
  const isReady = theme?.isReady;
  const [chartTheme, setChartTheme] = useState<ChartTheme>(LIGHT_FALLBACK);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const styles = window.getComputedStyle(document.documentElement);
    setChartTheme({
      colors: Array.from({ length: 8 }, (_, i) =>
        readVar(styles, `--chart-${i + 1}`, LIGHT_FALLBACK.colors[i]),
      ),
      grid: readVar(styles, "--c-chart-grid", LIGHT_FALLBACK.grid),
      axis: readVar(styles, "--c-chart-axis", LIGHT_FALLBACK.axis),
      label: readVar(styles, "--c-chart-label", LIGHT_FALLBACK.label),
      track: readVar(styles, "--c-chart-track", LIGHT_FALLBACK.track),
      surface: readVar(styles, "--c-surface", LIGHT_FALLBACK.surface),
    });
  }, [resolvedTheme, isReady]);

  return chartTheme;
}

/** Tone → hex for the current theme, used by the score gauges. */
export function useToneColors(): Record<string, string> {
  const theme = useOptionalTheme();
  const resolvedTheme = theme?.resolvedTheme;
  const isReady = theme?.isReady;
  const [tones, setTones] = useState<Record<string, string>>({
    success: "#17996b", brand: "#2469a8", warning: "#d98207", danger: "#d93a35",
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    const styles = window.getComputedStyle(document.documentElement);
    const rgb = (name: string, fallback: string) => {
      const raw = styles.getPropertyValue(name).trim();
      return raw ? `rgb(${raw})` : fallback;
    };
    setTones({
      success: rgb("--c-success-500", "#17996b"),
      brand: rgb("--c-brand-600", "#2469a8"),
      warning: rgb("--c-warning-500", "#d98207"),
      danger: rgb("--c-danger-500", "#d93a35"),
    });
  }, [resolvedTheme, isReady]);

  return tones;
}
