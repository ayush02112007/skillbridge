"use client";

import { useToneColors } from "@/hooks/use-chart-theme";
import { clamp, cn, scoreTone } from "@/lib/utils";

const TONE_BAR: Record<string, string> = {
  brand: "bg-brand-600",
  success: "bg-success-500",
  warning: "bg-warning-500",
  danger: "bg-danger-500",
  accent: "bg-accent-500",
  ink: "bg-ink-400",
};

export function Progress({
  value,
  tone,
  size = "md",
  className,
  label,
  showValue = false,
}: {
  value: number;
  tone?: keyof typeof TONE_BAR;
  size?: "sm" | "md" | "lg";
  className?: string;
  label?: string;
  showValue?: boolean;
}) {
  const percent = clamp(value);
  const resolvedTone = tone ?? scoreTone(percent);
  const height = { sm: "h-1.5", md: "h-2", lg: "h-2.5" }[size];

  return (
    <div className={cn("space-y-1.5", className)}>
      {(label || showValue) && (
        <div className="flex items-baseline justify-between gap-2">
          {label && <span className="text-xs font-medium text-ink-600">{label}</span>}
          {showValue && (
            <span className="text-xs font-semibold tabular-nums text-ink-800">
              {Math.round(percent)}%
            </span>
          )}
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={Math.round(percent)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ?? "Progress"}
        className={cn("w-full overflow-hidden rounded-full bg-ink-100", height)}
      >
        <div
          className={cn("h-full rounded-full transition-[width] duration-500 ease-out",
            TONE_BAR[resolvedTone] ?? TONE_BAR.brand)}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

/** Circular readiness gauge used on dashboards. */
export function ScoreRing({
  value,
  size = 128,
  strokeWidth = 10,
  label,
  sublabel,
}: {
  value: number;
  size?: number;
  strokeWidth?: number;
  label?: string;
  sublabel?: string;
}) {
  const tones = useToneColors();
  const percent = clamp(value);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;
  const tone = scoreTone(percent);
  const stroke = tones[tone];

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${label ?? "Score"}: ${Math.round(percent)} percent`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" className="stroke-ink-100" strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={stroke} strokeWidth={strokeWidth}
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 700ms cubic-bezier(0.22,1,0.36,1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-semibold tabular-nums text-ink-900">
          {Math.round(percent)}
          <span className="text-base text-ink-400">%</span>
        </span>
        {sublabel && (
          <span className="mt-0.5 max-w-[80%] text-center text-2xs leading-tight text-ink-500">
            {sublabel}
          </span>
        )}
      </div>
    </div>
  );
}
