/**
 * Shared API types for HeartGuardian AI.
 *
 * These mirror the backend's JSON shapes (see the design doc "Data Models"
 * and "API Endpoints"). They are hand-written for the MVP; once the backend
 * exposes OpenAPI they can be regenerated, but the names are kept stable so
 * screens and hooks do not need to change.
 *
 * All data in the MVP is synthetic and labeled experimental.
 */

// ---------------------------------------------------------------------------
// Core enums
// ---------------------------------------------------------------------------

export type MetricType = "hr" | "hrv" | "spo2" | "rhythm" | "activity" | "sleep";
export type Quality = "ok" | "low" | "missing";
export type Scenario = "A" | "B" | "C";
export type SimulatorStatus = "running" | "paused";
export type AlertState = "normal" | "trend_review" | "attention";
export type TrendRange = "daily" | "weekly" | "monthly";

export type ProviderKind = "doctor" | "hospital";
export type DispatchChannel = "simulated" | "real";
export type DispatchStatus = "pending_confirm" | "cancelled" | "sent" | "failed";
export type RoutingReason = "preferred_doctor_reachable" | "nearest_capable_hospital";

// ---------------------------------------------------------------------------
// Measurements & trends
// ---------------------------------------------------------------------------

export interface Reading {
  id?: number;
  timestamp: string; // ISO-8601 UTC
  metricType: MetricType;
  value: number | null; // null => missing / low-quality
  quality: Quality;
  isSynthetic: boolean;
  scenario: Scenario;
}

/** Envelope returned by GET /measurements (count + experimental flag + items). */
export interface MeasurementsResponse {
  count: number;
  isExperimental: boolean;
  items: Reading[];
}

/**
 * A single aggregated point on a trend series, as returned by GET /trends.
 * The backend aggregates per period and reports mean/min/max/count; `period`
 * is the bucket label (e.g. a date string).
 */
export interface TrendPoint {
  period: string;
  mean: number | null;
  min: number | null;
  max: number | null;
  count: number;
}

/** One metric's trend series plus its baseline mean, for the History screen. */
export interface TrendSeries {
  metric: MetricType;
  baselineMean: number | null;
  points: TrendPoint[];
}

export interface TrendsResponse {
  range: TrendRange;
  isExperimental: boolean;
  series: TrendSeries[];
}

// ---------------------------------------------------------------------------
// Alerts / insights
// ---------------------------------------------------------------------------

/** A supporting anomaly finding attached to an insight. */
export interface Finding {
  id?: number;
  metricType: MetricType;
  findingType: string;
  severityBand: string;
  windowStart: string;
  windowEnd: string;
  deviation: number | null;
  supporting: unknown;
  createdAt?: string;
}

/**
 * GET /insights returns a FLAT object (the current insight), not a wrapper.
 * This mirrors the backend `InsightResponse` exactly.
 */
export interface InsightResponse {
  state: AlertState;
  title: string;
  explanation: string;
  nextSteps: string;
  emergencyGuidance: string;
  experimentalLabel: string;
  isExperimental: boolean;
  findingIds: number[];
  findings: Finding[];
}

/** Summary returned by POST /analysis/run. */
export interface RunAnalysisResponse {
  findingsCount: number;
  alertState: AlertState;
  isExperimental: boolean;
}

/** A compact alert row for the History past-alerts list. */
export interface AlertSummary {
  state: AlertState;
  title: string;
  createdAt?: string;
}

// ---------------------------------------------------------------------------
// Simulator / scenario
// ---------------------------------------------------------------------------

export interface ScenarioState {
  scenario: Scenario;
  status: SimulatorStatus;
  seed: number;
  cursorTs: string | null;
  updatedAt: string;
}

// ---------------------------------------------------------------------------
// Care network & providers
// ---------------------------------------------------------------------------

export interface Provider {
  id: number;
  kind: ProviderKind;
  name: string;
  specialty?: string;
  canHandleCardiacEmergency: boolean;
  phone?: string;
  address?: string;
  lat: number;
  lon: number;
  isSynthetic: boolean;
}

export interface ProviderSuggestion {
  provider: Provider;
  distanceKm: number;
  isPreferred: boolean;
}

/** Envelope returned by GET /providers. */
export interface ProvidersResponse {
  count: number;
  isExperimental: boolean;
  items: ProviderSuggestion[];
}

export interface EmergencyContact {
  name: string;
  relationship?: string;
  phone: string;
  priority: number;
}

export interface CareProfile {
  fullName?: string;
  phone?: string;
  defaultLat?: number;
  defaultLon?: number;
  preferredProviderId?: number;
  emergencyContacts: EmergencyContact[];
}

// ---------------------------------------------------------------------------
// Emergency dispatch
// ---------------------------------------------------------------------------

export interface DispatchPayload {
  patient: { name?: string; phone?: string };
  location: { lat: number; lon: number; approximate: boolean; description?: string };
  emergencyContacts: EmergencyContact[];
  findingSummary: string; // non-diagnostic, experimental
  isExperimental: true;
}

export interface EmergencyDecision {
  recipient: Provider;
  routingReason: RoutingReason;
  payload: DispatchPayload;
  channel: DispatchChannel;
}

export interface DispatchEvent {
  id: number;
  alertId?: number;
  recipient?: Provider;
  routingReason: RoutingReason;
  channel: DispatchChannel;
  status: DispatchStatus;
  payload: DispatchPayload;
  createdAt: string;
}

// ---------------------------------------------------------------------------
// Settings & disclaimer
// ---------------------------------------------------------------------------

export interface Settings {
  warningsEnabled: boolean;
  suggestionsEnabled: boolean;
  emergencyEnabled: boolean;
  disclaimerAckAt: string | null;
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

/** Structured error body returned by the backend exception handlers. */
export interface ApiErrorBody {
  error: string;
  detail?: string;
}
