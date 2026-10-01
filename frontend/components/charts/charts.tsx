"use client";

/**
 * Chart primitives.
 *
 * Kept in one module so every chart in the product shares the same palette,
 * axis styling, tooltip and empty state. Colours are the brand ramp, ordered
 * so adjacent series stay distinguishable.
 */
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

import { EmptyState } from "@/components/ui/states";
import { useChartTheme } from "@/hooks/use-chart-theme";

/**
 * Light-theme series palette.
 *
 * Retained as a named export and as the fallback for the first render, before
 * the computed theme has been read. Live colours come from `useChartTheme()`,
 * which re-reads them whenever the theme changes.
 */
export const CHART_COLORS = [
  "#2469a8", "#17996b", "#ff8312", "#7c5cbf", "#0e7490",
  "#d93a35", "#b45309", "#515c76",
];

/** Axis styling for the current theme. Recharts needs concrete values here. */
function useAxisProps(axis: string, label: string) {
  return {
    stroke: axis,
    fontSize: 11,
    tickLine: false,
    axisLine: false,
    tick: { fill: label },
  } as const;
}

/**
 * Recharts passes its tooltip content whatever the active series holds and has
 * no exported type for it, so the shape is declared locally rather than `any`.
 */
interface TooltipEntry {
  dataKey?: string | number;
  name?: string | number;
  value?: number | string;
  color?: string;
  fill?: string;
  payload?: Record<string, unknown>;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: TooltipEntry[];
  label?: string | number;
}

function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-ink-200 bg-surface px-3 py-2 shadow-popover">
      {label !== undefined && (
        <p className="mb-1 text-xs font-medium text-ink-900">{label}</p>
      )}
      {payload.map((entry) => (
        <p key={entry.dataKey ?? entry.name} className="flex items-center gap-2 text-xs">
          <span
            className="size-2 rounded-full"
            style={{ background: entry.color ?? entry.fill }}
            aria-hidden
          />
          <span className="text-ink-600">{entry.name}:</span>
          <span className="font-semibold tabular-nums text-ink-900">
            {typeof entry.value === "number"
              ? entry.value.toLocaleString(undefined, { maximumFractionDigits: 1 })
              : entry.value}
          </span>
        </p>
      ))}
    </div>
  );
}

function ChartFrame({
  height = 260,
  isEmpty,
  emptyLabel,
  children,
}: {
  height?: number;
  isEmpty?: boolean;
  emptyLabel?: string;
  children: React.ReactElement;
}) {
  if (isEmpty) {
    return (
      <EmptyState
        className="py-10"
        title={emptyLabel ?? "No data yet"}
        description="This chart fills in as activity is recorded."
      />
    );
  }
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}

export function BarChartCard({
  data, xKey, bars, height = 260, emptyLabel, layout = "horizontal",
}: {
  data: Record<string, unknown>[];
  xKey: string;
  bars: { key: string; name: string; color?: string }[];
  height?: number;
  emptyLabel?: string;
  layout?: "horizontal" | "vertical";
}) {
  const theme = useChartTheme();
  const axisProps = useAxisProps(theme.axis, theme.label);
  const vertical = layout === "vertical";
  return (
    <ChartFrame height={height} isEmpty={!data.length} emptyLabel={emptyLabel}>
      <BarChart
        data={data}
        layout={layout}
        margin={{ top: 8, right: 12, bottom: 4, left: vertical ? 8 : 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} vertical={!vertical} />
        {vertical ? (
          <>
            <XAxis type="number" {...axisProps} />
            <YAxis dataKey={xKey} type="category" width={130} {...axisProps} />
          </>
        ) : (
          <>
            <XAxis dataKey={xKey} {...axisProps} />
            <YAxis {...axisProps} allowDecimals={false} />
          </>
        )}
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(36,105,168,0.06)" }} />
        {bars.length > 1 && <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />}
        {bars.map((bar, index) => (
          <Bar
            key={bar.key}
            dataKey={bar.key}
            name={bar.name}
            fill={bar.color ?? theme.colors[index % theme.colors.length]}
            radius={vertical ? [0, 4, 4, 0] : [4, 4, 0, 0]}
            maxBarSize={vertical ? 20 : 44}
          />
        ))}
      </BarChart>
    </ChartFrame>
  );
}

export function LineChartCard({
  data, xKey, lines, height = 260, emptyLabel, area = false,
}: {
  data: Record<string, unknown>[];
  xKey: string;
  lines: { key: string; name: string; color?: string }[];
  height?: number;
  emptyLabel?: string;
  area?: boolean;
}) {
  const theme = useChartTheme();
  const axisProps = useAxisProps(theme.axis, theme.label);
  const Chart = area ? AreaChart : LineChart;
  return (
    <ChartFrame height={height} isEmpty={!data.length} emptyLabel={emptyLabel}>
      <Chart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
        <defs>
          {lines.map((line, index) => (
            <linearGradient key={line.key} id={`grad-${line.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="0%"
                stopColor={line.color ?? theme.colors[index % theme.colors.length]}
                stopOpacity={0.22}
              />
              <stop
                offset="100%"
                stopColor={line.color ?? theme.colors[index % theme.colors.length]}
                stopOpacity={0}
              />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} vertical={false} />
        <XAxis dataKey={xKey} {...axisProps} />
        <YAxis {...axisProps} allowDecimals={false} />
        <Tooltip content={<ChartTooltip />} />
        {lines.length > 1 && <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />}
        {lines.map((line, index) => {
          const color = line.color ?? theme.colors[index % theme.colors.length];
          return area ? (
            <Area
              key={line.key}
              type="monotone"
              dataKey={line.key}
              name={line.name}
              stroke={color}
              strokeWidth={2}
              fill={`url(#grad-${line.key})`}
            />
          ) : (
            <Line
              key={line.key}
              type="monotone"
              dataKey={line.key}
              name={line.name}
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          );
        })}
      </Chart>
    </ChartFrame>
  );
}

export function DonutChartCard({
  data, height = 240, emptyLabel,
}: {
  data: { name: string; value: number; color?: string }[];
  height?: number;
  emptyLabel?: string;
}) {
  const theme = useChartTheme();
  const total = data.reduce((sum, item) => sum + item.value, 0);
  return (
    <ChartFrame height={height} isEmpty={!total} emptyLabel={emptyLabel}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius="58%"
          outerRadius="85%"
          paddingAngle={2}
          stroke="none"
        >
          {data.map((entry, index) => (
            <Cell
              key={entry.name}
              stroke={theme.surface}
              strokeWidth={2}
              fill={entry.color ?? theme.colors[index % theme.colors.length]}
            />
          ))}
        </Pie>
        <Tooltip content={<ChartTooltip />} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ChartFrame>
  );
}

export function RadarChartCard({
  data, height = 280, emptyLabel,
}: {
  data: { subject: string; you: number; required: number }[];
  height?: number;
  emptyLabel?: string;
}) {
  const theme = useChartTheme();
  return (
    <ChartFrame height={height} isEmpty={!data.length} emptyLabel={emptyLabel}>
      <RadarChart data={data} outerRadius="72%">
        <PolarGrid stroke={theme.grid} />
        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: theme.label }} />
        <PolarRadiusAxis domain={[0, 4]} tick={false} axisLine={false} />
        <Radar
          name="Role requires"
          dataKey="required"
          stroke={theme.axis}
          fill={theme.axis}
          fillOpacity={0.18}
        />
        <Radar
          name="You have"
          dataKey="you"
          stroke={theme.colors[0]}
          fill={theme.colors[0]}
          fillOpacity={0.35}
        />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        <Tooltip content={<ChartTooltip />} />
      </RadarChart>
    </ChartFrame>
  );
}

/** Horizontal funnel: stages with counts and conversion between them. */
export function FunnelChart({
  stages,
}: {
  stages: { stage: string; count: number }[];
}) {
  const theme = useChartTheme();
  const max = Math.max(...stages.map((s) => s.count), 1);
  if (!stages.length) {
    return <EmptyState title="No pipeline data yet" className="py-10" />;
  }
  return (
    <ol className="space-y-2.5">
      {stages.map((stage, index) => {
        const previous = index > 0 ? stages[index - 1].count : null;
        const conversion =
          previous && previous > 0 ? Math.round((stage.count / previous) * 100) : null;
        return (
          <li key={stage.stage}>
            <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
              <span className="font-medium text-ink-700">{stage.stage}</span>
              <span className="flex items-baseline gap-2">
                {conversion !== null && (
                  <span className="text-ink-400">{conversion}%</span>
                )}
                <span className="font-semibold tabular-nums text-ink-900">
                  {stage.count}
                </span>
              </span>
            </div>
            <div className="h-6 overflow-hidden rounded-md bg-ink-100">
              <div
                className="h-full rounded-md transition-[width] duration-500"
                style={{
                  width: `${Math.max(2, (stage.count / max) * 100)}%`,
                  background: theme.colors[index % theme.colors.length],
                  opacity: 1 - index * 0.1,
                }}
              />
            </div>
          </li>
        );
      })}
    </ol>
  );
}
