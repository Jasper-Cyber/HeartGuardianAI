import type { TrendSeries } from "@/api/types";
import { seriesHasData, seriesRange, shortLabel, toTrendChartData } from "@/utils/trends";

const points = [
  { timestamp: "2026-01-01T00:00:00Z", value: 10 },
  { timestamp: "2026-01-02T00:00:00Z", value: null },
  { timestamp: "2026-01-03T00:00:00Z", value: 30 },
];

describe("toTrendChartData", () => {
  it("bridges null values from the previous known value", () => {
    const data = toTrendChartData(points);
    expect(data.map((p) => p.value)).toEqual([10, 10, 30]);
  });

  it("skips leading nulls with no prior value", () => {
    const data = toTrendChartData([{ timestamp: "t", value: null }, { timestamp: "t2", value: 5 }]);
    expect(data.map((p) => p.value)).toEqual([5]);
  });

  it("labels every Nth point and flags anomalies", () => {
    const anomalies = new Set(["2026-01-03T00:00:00Z"]);
    const data = toTrendChartData(points, { labelEvery: 2, anomalyTimestamps: anomalies });
    expect(data[0].label).toBeDefined();
    expect(data[1].label).toBeUndefined();
    expect(data[2].anomaly).toBe(true);
  });
});

describe("shortLabel", () => {
  it("formats month/day", () => {
    expect(shortLabel("2026-03-09T00:00:00Z")).toBe("3/9");
  });
  it("returns empty for an invalid date", () => {
    expect(shortLabel("not-a-date")).toBe("");
  });
});

describe("seriesRange / seriesHasData", () => {
  const series: TrendSeries = {
    metricType: "hr",
    points,
    baselineMean: 20,
    baselineStd: 5,
  };

  it("computes min/max ignoring nulls", () => {
    expect(seriesRange(series)).toEqual({ min: 10, max: 30 });
  });

  it("reports no data when all points are null", () => {
    const empty: TrendSeries = { ...series, points: [{ timestamp: "t", value: null }] };
    expect(seriesRange(empty)).toBeNull();
    expect(seriesHasData(empty)).toBe(false);
    expect(seriesHasData(series)).toBe(true);
  });
});
