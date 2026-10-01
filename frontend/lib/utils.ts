import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Compact currency, e.g. 1500000 -> "₹15L". Indian conventions by default. */
export function formatCurrency(
  amount?: number | null,
  currency = "INR",
): string {
  if (amount === null || amount === undefined) return "—";
  if (currency === "INR") {
    if (amount >= 10_000_000) return `₹${(amount / 10_000_000).toFixed(1)}Cr`;
    if (amount >= 100_000) return `₹${(amount / 100_000).toFixed(amount % 100_000 === 0 ? 0 : 1)}L`;
    if (amount >= 1_000) return `₹${(amount / 1_000).toFixed(0)}k`;
    return `₹${amount}`;
  }
  return new Intl.NumberFormat("en", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatRange(
  min?: number | null,
  max?: number | null,
  currency = "INR",
): string {
  if (!min && !max) return "Not disclosed";
  if (min && max && min !== max)
    return `${formatCurrency(min, currency)} – ${formatCurrency(max, currency)}`;
  return formatCurrency(min ?? max, currency);
}

export function formatDate(value?: string | null, opts?: Intl.DateTimeFormatOptions) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    ...opts,
  }).format(date);
}

export function formatDateTime(value?: string | null) {
  return formatDate(value, { hour: "2-digit", minute: "2-digit" });
}

/** "3 days ago" / "in 5 days" — relative, with sensible thresholds. */
export function relativeTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  const diffMs = date.getTime() - Date.now();
  const diffDays = Math.round(diffMs / 86_400_000);
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

  if (Math.abs(diffDays) >= 30) {
    return formatter.format(Math.round(diffDays / 30), "month");
  }
  if (Math.abs(diffDays) >= 1) return formatter.format(diffDays, "day");
  const diffHours = Math.round(diffMs / 3_600_000);
  if (Math.abs(diffHours) >= 1) return formatter.format(diffHours, "hour");
  return formatter.format(Math.round(diffMs / 60_000), "minute");
}

export function daysUntil(value?: string | null): number | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return Math.ceil((date.getTime() - Date.now()) / 86_400_000);
}

export function initials(name?: string | null): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function titleCase(value?: string | null): string {
  if (!value) return "";
  return value
    .replace(/[_-]+/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function pluralise(count: number, singular: string, plural?: string) {
  return `${count} ${count === 1 ? singular : plural ?? `${singular}s`}`;
}

export function clamp(value: number, min = 0, max = 100) {
  return Math.min(max, Math.max(min, value));
}

/** Colour band for a 0-100 score, used consistently across the app. */
export function scoreTone(score: number): "danger" | "warning" | "brand" | "success" {
  if (score >= 80) return "success";
  if (score >= 60) return "brand";
  if (score >= 35) return "warning";
  return "danger";
}
