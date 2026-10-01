# Theming

SkillBridge ships a light and a dark theme. Both are designed; neither is an
inversion of the other.

---

## For users

The toggle sits in the header of every surface:

| Where | Control |
| --- | --- |
| Marketing site | Sun/moon button in the top navigation (and beside the hamburger on a phone) |
| Sign-in and registration | Sun/moon button in the page header |
| Every portal (student, industry, academician, institution, admin) | Sun/moon button in the app header, next to notifications |
| Settings → Account | A three-way control: **Light · Dark · System** |

**System** is the default. It follows the operating system's
`prefers-color-scheme` and *keeps* following it, so a machine that switches to
dark at sunset takes the app with it. Choosing Light or Dark explicitly stops
that following until the user picks System again.

The choice is stored in `localStorage` under `sb.theme` and survives reloads,
navigation and new tabs. It is per-device, not per-account: a shared
workstation does not force one person's preference onto the next.

---

## No flash of the wrong theme

The obvious implementation — read `localStorage` in a React effect — paints
light first and snaps to dark a frame later. Instead, a small synchronous
script runs in `<head>`, before the browser paints anything:

```tsx
// lib/theme.tsx — rendered into <head> by app/layout.tsx
export function ThemeScript() { /* reads localStorage, sets the class */ }
```

It resolves the theme and sets the `dark` class on `<html>` before first paint.
`ThemeProvider` then *adopts* that decision on mount rather than re-deciding
it, so there is nothing to correct.

Two consequences worth knowing:

- `<html>` carries `suppressHydrationWarning`, because the script legitimately
  changes the markup React rendered on the server.
- The colour transition is suppressed for the first frame via a
  `theme-switching` class, so the initial application is not animated. A
  deliberate switch afterwards *is* eased, over 180ms.

---

## Design tokens

Every colour resolves through a CSS variable defined in `app/globals.css`.
There is no component anywhere that hardcodes a colour, and no `dark:` variant
scattered through the markup — a theme is a set of values, not a set of
overrides.

Values are stored as space-separated RGB channels so Tailwind can compose them
with an alpha: `--c-ink-950: 29 32 41` lets `bg-ink-950/40` still work.

### The families

| Family | Steps | Used for |
| --- | --- | --- |
| `ink` | 50–950 | Text, borders, subtle fills — the structural neutral |
| `brand` | 50–950 | Links, emphasis, the primary data series |
| `accent` | 50–950 | Momentum: readiness, progress, achievement |
| `success` / `warning` / `danger` | 50, 500–700 | Status |
| `surface` | DEFAULT, muted, sunken, overlay | Cards, page, wells, dialogs |
| `primary` | DEFAULT, hover, active, fg | Solid interactive fills |
| `danger-solid` / `success-solid` | DEFAULT, hover | Destructive and confirming buttons |
| `canvas` | DEFAULT, soft, fg, muted | Surfaces that are dark in **both** themes |

### Coverage

| Element | Token |
| --- | --- |
| Page background | `surface-muted` |
| Cards, inputs, menus | `surface` |
| Dialogs, popovers | `surface-overlay` |
| Table headers, inset wells | `surface-sunken` |
| Primary text | `ink-950` (headings), `ink-800` (body) |
| Secondary text | `ink-500`, `ink-400` |
| Borders and dividers | `ink-200` |
| Hover fills | `ink-100` |
| Buttons (primary) | `primary` + `primary-fg` |
| Buttons (destructive / confirming) | `danger-solid` / `success-solid` |
| Buttons (secondary, ghost) | `surface` / `ink-100` on `ink-200` |
| Inputs | `surface` on `ink-200`, invalid `danger-500` |
| Navigation | `surface`, active item `brand-50` + `brand-700` |
| Tables | `surface` rows, `ink-200` rules |
| Modal scrim | `canvas/60` |
| Alerts and toasts | `{status}-50` fill, `{status}-500` border, `{status}-600/700` text |
| Badges and status chips | `{status}-50` fill, `{status}-700` text |
| Charts: series | `--chart-1` … `--chart-8` |
| Charts: grid, axis, labels | `--c-chart-grid`, `--c-chart-axis`, `--c-chart-label` |
| Gauges and progress tracks | `--c-chart-track` |
| Skeletons | `ink-100` |
| Focus ring | `brand-600`, offset in `surface` |
| Scrollbars | `ink-300` on `surface-muted` |
| Shadows | `--c-shadow` with per-theme alpha |

### The two families that do not flip

Most tokens move together: `ink-800` is dark text on a light page and light
text on a dark one. Two families deliberately do not.

**`canvas`** is dark in both themes. The marketing hero, the sign-in aside
panel, code blocks and modal scrims are dark *by design*. Flipping them with
the neutral ramp would turn a deliberate dark panel into a white slab with
white text on it.

**`primary`** exists because a button fill and link text need to move in
opposite directions. In light mode both can be `brand-700`. In dark mode, link
text must get *lighter* to read against a dark card, while a button fill must
stay *dark* enough for a white label. One token cannot do both, so solid fills
use `primary` and text uses the `brand` ramp.

---

## Accessibility

Every text token was checked against the surface it sits on. Measured
contrast ratios in dark mode, against `surface` (#161b24) and `surface-muted`
(#0d1117):

| Token | vs card | vs page | Level |
| --- | --- | --- | --- |
| `ink-400` (muted icons) | 4.80 | 5.12 | AA |
| `ink-500` (secondary text) | 6.69 | 7.15 | AA |
| `ink-600` | 8.63 | 9.21 | AAA |
| `ink-800` (body) | 13.14 | 14.03 | AAA |
| `ink-950` (headings) | 16.24 | 17.34 | AAA |
| `brand-700` (links) | 8.72 | 9.31 | AAA |
| `success-600` | 9.34 | 9.98 | AAA |
| `warning-500` | 9.35 | 9.98 | AAA |
| `danger-500` | 6.30 | 6.73 | AA |
| `danger-600` | 7.49 | 8.00 | AAA |
| `accent-400` | 9.63 | 10.28 | AAA |

`primary` carries a white label at 5.00:1, and stands out from the card it sits
on at 3.45:1 — above the 3:1 required for a UI component boundary.

Also handled:

- `color-scheme` is set on `<html>`, so native form controls, the caret and
  default scrollbars follow the theme instead of staying light.
- `themeColor` is declared per scheme, so mobile browser chrome matches.
- The toggle's accessible name states the *action* ("Switch to dark theme"),
  not the current state — a sun icon alone is ambiguous.
- The three-way control is a proper `radiogroup` with `aria-checked`.
- The colour transition is disabled under `prefers-reduced-motion: reduce`.

---

## Working with the theme

### Styling a new component

Use the semantic classes. They already work in both themes:

```tsx
<div className="rounded-xl border border-ink-200 bg-surface p-4 shadow-card">
  <h3 className="text-ink-950">Title</h3>
  <p className="text-sm text-ink-500">Secondary copy</p>
</div>
```

Do not write `dark:` variants, and do not hardcode a hex value. If a colour
seems to be missing, it belongs in `globals.css` as a token.

### Colour inside an SVG or a canvas

SVG *presentation attributes* do not resolve `var()`, which is the one place
the token system cannot reach directly. Two options:

```tsx
// A class sets the CSS property, which does resolve the variable.
<circle className="stroke-ink-100" />

// Or read the computed value — needed where a library wants a real string.
const theme = useChartTheme();
<CartesianGrid stroke={theme.grid} />
```

`hooks/use-chart-theme.ts` provides `useChartTheme()` for Recharts and
`useToneColors()` for the score gauges. Both re-read on every theme change,
and both work outside `ThemeProvider` — a design-system primitive should not
throw just because it is rendered in isolation.

### Reading the theme in code

```tsx
const { theme, resolvedTheme, setTheme, toggleTheme, isReady } = useTheme();
```

`theme` is the user's choice, including `"system"`. `resolvedTheme` is what is
actually on screen. `isReady` is false until the client has mounted — guard
anything that would otherwise render the wrong state during hydration.

---

## Tests

`frontend/tests/unit/theme.test.tsx` (13 tests) covers the behaviours a user
would notice and struggle to diagnose:

- the system preference is the default, and a stored choice beats it;
- a corrupted stored value falls back instead of failing to render;
- toggling persists, and survives `localStorage` throwing;
- "System" keeps following the OS, and an explicit choice stops it;
- `color-scheme` and `data-theme` are set for native controls;
- the three-way control exposes real radios with the right `aria-checked`.

`frontend/tests/e2e/theme.spec.ts` (8 tests) covers what only a real browser
can show:

- the toggle is present and effective on the marketing page, the sign-in page
  and inside a portal;
- the choice follows the user across navigations;
- it survives a reload, and the `dark` class, `color-scheme` and painted
  background are all already correct at `DOMContentLoaded` — with a blocking
  inline script in `<head>` doing it, not a React effect;
- a stored choice beats a conflicting system preference, and the system
  preference is followed when nothing is stored;
- eight representative pages — public, auth and all the portals — paint in
  both themes with the page heading above 4.5:1 against the background, which
  is what a missed token would break.
