/**
 * Care-network API hooks + types (Tasks 24-25, Owner: maiabrunne).
 *
 * Self-contained so the provider-suggestion and emergency screens are not blocked
 * on Helenawai's shared `api/client.ts` (Task 13). When that lands, the `apiFetch`
 * helper here can be swapped for the shared client with no change to call sites,
 * and these care-specific types can move into `api/types.ts`.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

// ---------------------------------------------------------------------------
// Base URL: localhost for the simulator/web; override via EXPO_PUBLIC_API_URL
// (e.g. your machine's LAN IP when running on a physical phone with Expo Go).
// ---------------------------------------------------------------------------
export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail ?? body.error ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

// ---------------------------------------------------------------------------
// Types (mirror the backend shapes)
// ---------------------------------------------------------------------------
export type ProviderKind = "doctor" | "hospital";
export type DispatchChannel = "simulated" | "real";
export type RoutingReason =
  | "preferred_doctor_reachable"
  | "nearest_capable_hospital";

export interface Provider {
  id: number;
  kind: ProviderKind;
  name: string;
  specialty?: string | null;
  canHandleCardiacEmergency: boolean;
  phone?: string | null;
  address?: string | null;
  lat: number;
  lon: number;
  isSynthetic: boolean;
}

export interface ProviderSuggestion {
  provider: Provider;
  distanceKm: number;
  isPreferred: boolean;
}

export interface EmergencyContact {
  name: string;
  relationship?: string | null;
  phone: string;
  priority: number;
}

export interface DispatchPayload {
  patient: { name?: string | null; phone?: string | null };
  location: {
    lat: number;
    lon: number;
    approximate: boolean;
    description?: string | null;
  };
  emergencyContacts: EmergencyContact[];
  findingSummary: string;
  isExperimental: true;
}

export interface EmergencyDecision {
  recipient: Provider;
  routingReason: RoutingReason;
  payload: DispatchPayload;
  channel: DispatchChannel;
}

export interface EmergencyEvaluation {
  decision: EmergencyDecision | null;
  enabled: boolean;
  emergencyGuidance: string;
  notice: string;
}

export interface DispatchResult {
  id: number;
  status: "pending_confirm" | "cancelled" | "sent" | "failed";
  channel: DispatchChannel;
  detail: string;
  emergencyGuidance?: string;
  notice?: string;
}

export interface DispatchEvent {
  id: number;
  alertId: number | null;
  recipientProviderId: number | null;
  routingReason: RoutingReason;
  channel: DispatchChannel;
  status: string;
  /** Stored as JSON text by the backend; use `parseDispatchPayload` to read it. */
  payload: string;
  createdAt: string;
}

/** Safely parse a dispatch event's JSON payload string. Returns null on bad data. */
export function parseDispatchPayload(payload: string): DispatchPayload | null {
  try {
    return JSON.parse(payload) as DispatchPayload;
  } catch {
    return null;
  }
}

export interface Settings {
  warningsEnabled: boolean;
  suggestionsEnabled: boolean;
  emergencyEnabled: boolean;
  disclaimerAckAt: string | null;
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------
export function useSettings() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: () => apiFetch<Settings>("/settings"),
  });
}

export function useProviders(
  lat: number | null,
  lon: number | null,
  emergency: boolean,
) {
  return useQuery({
    queryKey: ["providers", lat, lon, emergency],
    enabled: lat != null && lon != null,
    queryFn: () =>
      apiFetch<{ suggestions: ProviderSuggestion[]; isSynthetic: boolean }>(
        `/providers?lat=${lat}&lon=${lon}&emergency=${emergency}`,
      ),
  });
}

export interface EvaluateArgs {
  alertState: string;
  lat: number | null;
  lon: number | null;
  locationApproximate?: boolean;
}

export function useEmergencyEvaluation() {
  return useMutation({
    mutationFn: (args: EvaluateArgs) =>
      apiFetch<EmergencyEvaluation>("/emergency/evaluate", {
        method: "POST",
        body: JSON.stringify(args),
      }),
  });
}

export interface DispatchArgs {
  decision: EmergencyDecision;
  confirmed: boolean;
  channel?: DispatchChannel;
  alertId?: number | null;
}

export function useDispatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: DispatchArgs) =>
      apiFetch<DispatchResult>("/emergency/dispatch", {
        method: "POST",
        body: JSON.stringify(args),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["dispatchHistory"] });
    },
  });
}

export function useDispatchHistory() {
  return useQuery({
    queryKey: ["dispatchHistory"],
    queryFn: () =>
      apiFetch<{ events: DispatchEvent[] }>("/emergency/history"),
  });
}
