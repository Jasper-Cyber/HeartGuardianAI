/**
 * Care-network API hooks + types (Tasks 24-25, Owner: maiabrunne).
 *
 * Wired to the merged backend contract (Tasks 19/20 routers): `/providers`,
 * `/care/profile`, `/settings`, and `/emergency/{evaluate,dispatch,history}`.
 * Self-contained so the mobile screens aren't blocked on Helenawai's shared
 * `api/client.ts` (Task 13); when that lands, `apiFetch` can be swapped for it
 * and these types moved into `api/types.ts`.
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
// Types (mirror the merged backend shapes)
// ---------------------------------------------------------------------------
export type ProviderKind = "doctor" | "hospital";
export type DispatchChannel = "simulated" | "real";

export interface Provider {
  id: number | null;
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

/** GET /providers response (Task 19 contract). */
export interface SuggestionsResponse {
  count: number;
  isExperimental: boolean;
  items: ProviderSuggestion[];
}

export interface EmergencyContact {
  name: string;
  relationship?: string | null;
  phone: string;
  priority: number;
}

export interface CareProfile {
  fullName?: string | null;
  phone?: string | null;
  defaultLat?: number | null;
  defaultLon?: number | null;
  preferredProviderId?: number | null;
  emergencyContacts: EmergencyContact[];
}

/** POST /emergency/evaluate response — flat DecisionOut (Task 20 contract). */
export interface EmergencyDecision {
  enabled: boolean;
  recipientProviderId?: number | null;
  recipientName?: string | null;
  routingReason?: string | null;
  payload?: Record<string, unknown> | null;
  channel?: DispatchChannel | null;
  emergencyGuidance: string;
  isExperimental: boolean;
}

/** POST /emergency/dispatch response (Task 20 contract). */
export interface DispatchResult {
  id: number | null;
  recipientProviderId: number | null;
  routingReason: string;
  channel: DispatchChannel;
  status: "pending_confirm" | "cancelled" | "sent" | "failed";
  payload: Record<string, unknown>;
  emergencyGuidance: string;
  isExperimental: boolean;
}

/** GET /emergency/history item (flat; no payload) (Task 20 contract). */
export interface DispatchHistoryItem {
  id: number | null;
  recipientProviderId: number | null;
  routingReason: string;
  channel: DispatchChannel;
  status: string;
  createdAt?: string | null;
}

export interface Settings {
  warningsEnabled: boolean;
  suggestionsEnabled: boolean;
  emergencyEnabled: boolean;
  disclaimerAckAt: string | null;
  updatedAt?: string | null;
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

export function useCareProfile() {
  return useQuery({
    queryKey: ["careProfile"],
    queryFn: () => apiFetch<CareProfile | null>("/care/profile"),
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
      apiFetch<SuggestionsResponse>(
        `/providers?lat=${lat}&lon=${lon}&emergency=${emergency}`,
      ),
  });
}

export interface EvaluateArgs {
  lat: number | null;
  lon: number | null;
  findingSummary?: string;
}

export function useEmergencyEvaluation() {
  return useMutation({
    mutationFn: (args: EvaluateArgs) =>
      apiFetch<EmergencyDecision>("/emergency/evaluate", {
        method: "POST",
        body: JSON.stringify({
          lat: args.lat,
          lon: args.lon,
          findingSummary: args.findingSummary ?? "Experimental monitoring signal.",
        }),
      }),
  });
}

export interface DispatchArgs {
  lat: number | null;
  lon: number | null;
  findingSummary?: string;
  channel?: DispatchChannel;
  confirmed: boolean;
  alertId?: number | null;
}

export function useDispatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: DispatchArgs) =>
      apiFetch<DispatchResult>("/emergency/dispatch", {
        method: "POST",
        body: JSON.stringify({
          lat: args.lat,
          lon: args.lon,
          findingSummary: args.findingSummary ?? "Experimental monitoring signal.",
          channel: args.channel ?? "simulated",
          confirmed: args.confirmed,
          alertId: args.alertId ?? null,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["dispatchHistory"] });
    },
  });
}

export function useDispatchHistory() {
  return useQuery({
    queryKey: ["dispatchHistory"],
    queryFn: () => apiFetch<DispatchHistoryItem[]>("/emergency/history"),
  });
}
