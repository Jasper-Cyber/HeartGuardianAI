/**
 * Typed fetch wrapper for the HeartGuardian AI backend.
 *
 * Base URL resolution:
 *  1. `EXPO_PUBLIC_API_URL` env var (set this to your machine's LAN IP when
 *     running on a physical phone, e.g. http://192.168.1.20:8000).
 *  2. Otherwise, derive the host from the Expo dev-server host so the app on a
 *     device/simulator talks back to the computer running Metro.
 *  3. Fall back to http://localhost:8000 (web / iOS simulator).
 *
 * Everything here is local, synthetic, and experimental — no credentials.
 */
import Constants from "expo-constants";

import type {
  ApiErrorBody,
  CareProfile,
  DispatchChannel,
  DispatchEvent,
  EmergencyDecision,
  InsightsResponse,
  Provider,
  Reading,
  Scenario,
  ScenarioState,
  Settings,
  TrendRange,
  TrendsResponse,
} from "./types";

const DEFAULT_PORT = 8000;

/** Resolve the backend base URL for the current runtime. */
export function resolveBaseUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL;
  if (fromEnv && fromEnv.length > 0) return fromEnv.replace(/\/$/, "");

  // Expo SDK exposes the dev-server host (e.g. "192.168.1.20:8081"); reuse the
  // host so a physical device reaches the same machine on the API port.
  const hostUri =
    Constants.expoConfig?.hostUri ??
    // @ts-expect-error legacy manifest field, still present in some runtimes
    (Constants.manifest2?.extra?.expoClient?.hostUri as string | undefined) ??
    // @ts-expect-error legacy manifest field
    (Constants.manifest?.debuggerHost as string | undefined);

  if (hostUri) {
    const host = hostUri.split(":")[0];
    if (host) return `http://${host}:${DEFAULT_PORT}`;
  }

  return `http://localhost:${DEFAULT_PORT}`;
}

export const BASE_URL = resolveBaseUrl();

/** Error thrown for non-2xx responses, carrying the structured backend body when present. */
export class ApiError extends Error {
  readonly status: number;
  readonly body?: ApiErrorBody;

  constructor(status: number, message: string, body?: ApiErrorBody) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT";
  query?: Record<string, string | number | boolean | undefined>;
  body?: unknown;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const base = `${BASE_URL}/${path.replace(/^\//, "")}`;
  if (!query) return base;

  // Build the query string manually rather than relying on the URL /
  // URLSearchParams globals, whose React Native implementations are
  // inconsistent across runtimes.
  const pairs: string[] = [];
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined) {
      pairs.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
    }
  }
  return pairs.length > 0 ? `${base}?${pairs.join("&")}` : base;
}

/** Core request helper: JSON in, typed JSON out, structured errors. */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", query, body, signal } = options;

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (cause) {
    // Network failure (backend down, wrong LAN IP, etc.).
    throw new ApiError(0, `Network request to ${path} failed`, {
      error: "network_error",
      detail: cause instanceof Error ? cause.message : String(cause),
    });
  }

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const parsed = isJson ? await response.json().catch(() => undefined) : undefined;

  if (!response.ok) {
    const errBody = parsed as ApiErrorBody | undefined;
    throw new ApiError(
      response.status,
      errBody?.error ?? `Request to ${path} failed with ${response.status}`,
      errBody,
    );
  }

  return parsed as T;
}

// ---------------------------------------------------------------------------
// Endpoint methods — one per backend route the mobile app consumes.
// ---------------------------------------------------------------------------

export const api = {
  health: (signal?: AbortSignal) => request<{ status: string }>("/health", { signal }),

  // Measurements & trends
  getMeasurements: (
    params: { metric?: string; from?: string; to?: string } = {},
    signal?: AbortSignal,
  ) => request<Reading[]>("/measurements", { query: params, signal }),

  getTrends: (range: TrendRange, signal?: AbortSignal) =>
    request<TrendsResponse>("/trends", { query: { range }, signal }),

  // Analysis & insights
  runAnalysis: () => request<InsightsResponse>("/analysis/run", { method: "POST" }),

  getInsights: (signal?: AbortSignal) => request<InsightsResponse>("/insights", { signal }),

  // Simulator / scenario
  getScenario: (signal?: AbortSignal) => request<ScenarioState>("/scenario", { signal }),

  setScenario: (scenario: Scenario) =>
    request<ScenarioState>("/scenario", { method: "POST", body: { scenario } }),

  simulatorStart: () => request<ScenarioState>("/simulator/start", { method: "POST" }),
  simulatorPause: () => request<ScenarioState>("/simulator/pause", { method: "POST" }),
  simulatorReset: () => request<ScenarioState>("/simulator/reset", { method: "POST" }),

  // Care profile (Task 22 consumer; endpoint owned by maiabrunne)
  getCareProfile: (signal?: AbortSignal) => request<CareProfile>("/care/profile", { signal }),

  updateCareProfile: (profile: CareProfile) =>
    request<CareProfile>("/care/profile", { method: "PUT", body: profile }),

  // Providers (care/emergency consumers)
  getProviders: (
    params: { lat: number; lon: number; emergency?: boolean },
    signal?: AbortSignal,
  ) => request<Provider[]>("/providers", { query: params, signal }),

  // Emergency
  evaluateEmergency: (body: { lat: number; lon: number }) =>
    request<EmergencyDecision | null>("/emergency/evaluate", { method: "POST", body }),

  dispatchEmergency: (body: { channel: DispatchChannel; confirm: boolean }) =>
    request<DispatchEvent>("/emergency/dispatch", { method: "POST", body }),

  getDispatchHistory: (signal?: AbortSignal) =>
    request<DispatchEvent[]>("/emergency/history", { signal }),

  // Settings & disclaimer
  getSettings: (signal?: AbortSignal) => request<Settings>("/settings", { signal }),

  updateSettings: (patch: Partial<Settings>) =>
    request<Settings>("/settings", { method: "PUT", body: patch }),

  ackDisclaimer: () => request<Settings>("/settings/disclaimer-ack", { method: "POST" }),
};

export type Api = typeof api;
