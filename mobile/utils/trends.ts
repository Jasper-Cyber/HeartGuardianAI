/**
 * Chart data transforms for the History screen. Pure + testable (Task 27).
 */
import type { TrendPoint, TrendSeries } from "@/api/types";

export interface ChartPoint {
  value: number;
  /** Short x-axis label (derived from the timestamp). */
  label?: string;
  /** Marks a point flagged as anomalous so the chart can emphasize it. */
  anomaly?: boolean;
}

/**
 * Convert a trend series into gifted-charts points. Missing values (null) are
 * bridged from the previous known value so the line stays continuous; a point
 * with no prior value is skipped. Optionally thins labels to avoid clutter.
 */
export function toTrendChartData(
  points: TrendPoint[],
  options: { labelEvery?: number; anomalyTimestamps?: Set<string> } = {},
): ChartPoint[] {
  const { labelEvery = 0, anomalyTimestamps } = options;
  const out: ChartPoint[] = [];
  let last: number | null = null;

  points.forEach((p, i) => {
    const resolved: number | null = p.value ?? last;
    if (resolved === null || Number.isNaN(resolved)) return;
    last = resolved;

    const point: ChartPoint = { value: resolved };
    if (labelEvery > 0 && i % labelEvery === 0) point.label = shortLabel(p.timestamp);
    if (anomalyTimestamps?.has(p.timestamp)) point.anomaly = true;
    out.push(point);
  });

  return out;
}

/**
 * A compact axis label (month/day) from an ISO timestamp. Uses UTC getters so
 * the label is deterministic regardless of the device's timezone.
 */
export function shortLabel(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${d.getUTCMonth() + 1}/${d.getUTCDate()}`;
}

/** Min/max across a series' resolved values, for chart scaling. Null when empty. */
export function seriesRange(series: TrendSeries): { min: number; max: number } | null {
  const values = series.points
    .map((p) => p.value)
    .filter((v): v is number => v !== null && !Number.isNaN(v));
  if (values.length === 0) return null;
  return { min: Math.min(...values), max: Math.max(...values) };
}

/** Whether a series has at least one usable data point. */
export function seriesHasData(series: TrendSeries): boolean {
  return series.points.some((p) => p.value !== null && !Number.isNaN(p.value));
}
