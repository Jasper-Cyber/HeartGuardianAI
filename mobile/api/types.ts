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
  timestamp: string; // ISO-8601 UTC
  metricType: MetricType;
  value: number | null; // null => missing / low-quality
  quality: Quality;
  isSynthetic: true;
  scenario: Scenario;
}

/** A single aggregated point on a trend series. */
export interface TrendPoint {
  timestamp: string;
  value: number | null;
}

/** One metric's trend series plus its baseline band, for the History screen. */
export interface TrendSeries {
  metricType: MetricType;
  points: TrendPoint[];
  baselineMean: number | null;
  baselineStd: number | null;
}

export interface TrendsResponse {
  range: TrendRange;
  series: TrendSeries[];
}

// ---------------------------------------------------------------------------
// Alerts / insights
// ---------------------------------------------------------------------------

export interface Alert {
  id?: number;
  state: AlertState;
  title: string;
  explanation: string;
  nextSteps: string;
  isExperimental: true;
  emergencyGuidance: string;
  createdAt?: string;
}

/** Response of GET /insights: the current alert plus recent history. */
export interface InsightsResponse {
  current: Alert;
  history: Alert[];
}

// ---------------------------------------------------------------------------
// Simulator / scenario
// ---------------------------------------------------------------------------

export interface ScenarioState {
  scenario: Scenario;
  status: SimulatorStatus;
  seed: number;
  updatedAt?: string;
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
  isSynthetic: true;
}

export interface ProviderSuggestion {
  provider: Provider;
  distanceKm: number;
  isPreferred: boolean;
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
