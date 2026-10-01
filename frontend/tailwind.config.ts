import type { Config } from "tailwindcss";

/**
 * SkillBridge visual identity.
 *
 * The palette is deliberately its own: a deep "ink" neutral for structure, a
 * considered academic blue as the primary, and a warm accent used sparingly for
 * momentum (progress, readiness, achievement). It is not a clone of any other
 * product's system.
 */
const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
  ],
  theme: {
    container: { center: true, padding: "1.5rem", screens: { "2xl": "1400px" } },
    extend: {
      colors: {
        ink: {
          50: "rgb(var(--c-ink-50) / <alpha-value>)",
          100: "rgb(var(--c-ink-100) / <alpha-value>)",
          200: "rgb(var(--c-ink-200) / <alpha-value>)",
          300: "rgb(var(--c-ink-300) / <alpha-value>)",
          400: "rgb(var(--c-ink-400) / <alpha-value>)",
          500: "rgb(var(--c-ink-500) / <alpha-value>)",
          600: "rgb(var(--c-ink-600) / <alpha-value>)",
          700: "rgb(var(--c-ink-700) / <alpha-value>)",
          800: "rgb(var(--c-ink-800) / <alpha-value>)",
          900: "rgb(var(--c-ink-900) / <alpha-value>)",
          950: "rgb(var(--c-ink-950) / <alpha-value>)",
        },
        brand: {
          50: "rgb(var(--c-brand-50) / <alpha-value>)",
          100: "rgb(var(--c-brand-100) / <alpha-value>)",
          200: "rgb(var(--c-brand-200) / <alpha-value>)",
          300: "rgb(var(--c-brand-300) / <alpha-value>)",
          400: "rgb(var(--c-brand-400) / <alpha-value>)",
          500: "rgb(var(--c-brand-500) / <alpha-value>)",
          600: "rgb(var(--c-brand-600) / <alpha-value>)",
          700: "rgb(var(--c-brand-700) / <alpha-value>)",
          800: "rgb(var(--c-brand-800) / <alpha-value>)",
          900: "rgb(var(--c-brand-900) / <alpha-value>)",
          950: "rgb(var(--c-brand-950) / <alpha-value>)",
        },
        accent: {
          50: "rgb(var(--c-accent-50) / <alpha-value>)",
          100: "rgb(var(--c-accent-100) / <alpha-value>)",
          200: "rgb(var(--c-accent-200) / <alpha-value>)",
          300: "rgb(var(--c-accent-300) / <alpha-value>)",
          400: "rgb(var(--c-accent-400) / <alpha-value>)",
          500: "rgb(var(--c-accent-500) / <alpha-value>)",
          600: "rgb(var(--c-accent-600) / <alpha-value>)",
          700: "rgb(var(--c-accent-700) / <alpha-value>)",
          800: "rgb(var(--c-accent-800) / <alpha-value>)",
          900: "rgb(var(--c-accent-900) / <alpha-value>)",
          950: "rgb(var(--c-accent-950) / <alpha-value>)",
        },
        success: {
          50: "rgb(var(--c-success-50) / <alpha-value>)",
          500: "rgb(var(--c-success-500) / <alpha-value>)",
          600: "rgb(var(--c-success-600) / <alpha-value>)",
          700: "rgb(var(--c-success-700) / <alpha-value>)",
        },
        warning: {
          50: "rgb(var(--c-warning-50) / <alpha-value>)",
          500: "rgb(var(--c-warning-500) / <alpha-value>)",
          600: "rgb(var(--c-warning-600) / <alpha-value>)",
        },
        danger: {
          50: "rgb(var(--c-danger-50) / <alpha-value>)",
          500: "rgb(var(--c-danger-500) / <alpha-value>)",
          600: "rgb(var(--c-danger-600) / <alpha-value>)",
          700: "rgb(var(--c-danger-700) / <alpha-value>)",
        },
        surface: {
          DEFAULT: "rgb(var(--c-surface) / <alpha-value>)",
          muted: "rgb(var(--c-surface-muted) / <alpha-value>)",
          sunken: "rgb(var(--c-surface-sunken) / <alpha-value>)",
          overlay: "rgb(var(--c-surface-overlay) / <alpha-value>)",
        },
        // Solid interactive fills. Separate from the `brand` ramp because a
        // button background and link text need to move in opposite directions
        // between themes: the fill stays deep enough for a white label, the
        // text gets lighter so it stays readable on a dark card.
        primary: {
          DEFAULT: "rgb(var(--c-primary) / <alpha-value>)",
          hover: "rgb(var(--c-primary-hover) / <alpha-value>)",
          active: "rgb(var(--c-primary-active) / <alpha-value>)",
          fg: "rgb(var(--c-primary-fg) / <alpha-value>)",
        },
        "danger-solid": {
          DEFAULT: "rgb(var(--c-danger-solid) / <alpha-value>)",
          hover: "rgb(var(--c-danger-solid-hover) / <alpha-value>)",
        },
        "success-solid": {
          DEFAULT: "rgb(var(--c-success-solid) / <alpha-value>)",
          hover: "rgb(var(--c-success-solid-hover) / <alpha-value>)",
        },
        // Always dark, in both themes: the marketing hero, the sign-in aside,
        // modal scrims and code blocks are dark by design, not by theme.
        canvas: {
          DEFAULT: "rgb(var(--c-canvas) / <alpha-value>)",
          soft: "rgb(var(--c-canvas-soft) / <alpha-value>)",
          fg: "rgb(var(--c-canvas-fg) / <alpha-value>)",
          muted: "rgb(var(--c-canvas-muted) / <alpha-value>)",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      borderRadius: {
        xl: "0.875rem", "2xl": "1.125rem", "3xl": "1.5rem",
      },
      boxShadow: {
        // Deliberately soft: structure comes from borders, not heavy shadows.
        // The alpha is a variable because a shadow tuned for a white page is
        // invisible on a dark one.
        card: "0 1px 2px rgb(var(--c-shadow) / var(--shadow-weak)), 0 1px 3px rgb(var(--c-shadow) / var(--shadow-soft))",
        lifted: "0 2px 4px rgb(var(--c-shadow) / var(--shadow-weak)), 0 8px 24px rgb(var(--c-shadow) / var(--shadow-medium))",
        popover: "0 4px 6px rgb(var(--c-shadow) / var(--shadow-weak)), 0 12px 32px rgb(var(--c-shadow) / var(--shadow-strong))",
      },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "theme-in": {
          from: { opacity: "0", transform: "rotate(-35deg) scale(0.7)" },
          to: { opacity: "1", transform: "rotate(0deg) scale(1)" },
        },
      },
      animation: {
        "fade-in": "fade-in 200ms ease-out",
        "slide-up": "slide-up 260ms cubic-bezier(0.22, 1, 0.36, 1)",
        "theme-in": "theme-in 260ms cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
