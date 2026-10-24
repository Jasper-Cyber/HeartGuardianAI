import { useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import {
  useDispatch,
  useDispatchHistory,
  useEmergencyEvaluation,
  useSettings,
  type EmergencyDecision,
} from "@/api/care";
import { DispatchHistoryList } from "@/components/DispatchHistoryList";
import { EmergencyConfirmDialog } from "@/components/EmergencyConfirmDialog";
import { SimulatedDispatchBadge } from "@/components/SimulatedDispatchBadge";
import { useUserLocation } from "@/components/useUserLocation";
import { theme } from "@/theme";

/**
 * Emergency-response flow (Task 25, Owner: maiabrunne).
 *
 * Only runs when the feature is enabled (Req 11.1). Evaluates the routing decision,
 * previews the recipient + payload, and gates dispatch behind the confirm-with-
 * countdown dialog (Req 11.5). Simulated by default with a simulated/real badge
 * (Req 11.6). Static emergency-services guidance is always shown (Req 11.8), and
 * past dispatches are listed (Req 11.7).
 */
export default function EmergencyScreen() {
  const params = useLocalSearchParams<{ alertState?: string }>();
  const alertState = params.alertState ?? "attention";

  const settings = useSettings();
  const location = useUserLocation();
  const evaluate = useEmergencyEvaluation();
  const dispatch = useDispatch();
  const history = useDispatchHistory();

  const [decision, setDecision] = useState<EmergencyDecision | null>(null);
  const [guidance, setGuidance] = useState<string>("");
  const [notice, setNotice] = useState<string>("");
  const [confirming, setConfirming] = useState(false);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const enabled = settings.data?.emergencyEnabled ?? false;

  // Evaluate once location + settings are ready and the feature is enabled.
  useEffect(() => {
    if (!enabled || !location.resolved) return;
    evaluate.mutate(
      { alertState, lat: location.lat, lon: location.lon, locationApproximate: location.approximate },
      {
        onSuccess: (res) => {
          setDecision(res.decision);
          setGuidance(res.emergencyGuidance);
          setNotice(res.notice);
        },
      },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, location.resolved, alertState]);

  const onConfirm = () => {
    if (!decision) return;
    dispatch.mutate(
      { decision, confirmed: true },
      {
        onSuccess: (res) => {
          setLastResult(res.detail);
          setConfirming(false);
          void history.refetch();
        },
        onError: (err) => {
          setLastResult((err as Error).message);
          setConfirming(false);
        },
      },
    );
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.h1}>Emergency response</Text>
        {notice ? <Text style={styles.notice}>{notice}</Text> : null}

        {/* Static guidance is ALWAYS shown, independent of dispatch (Req 11.8). */}
        <View style={styles.guidanceCard}>
          <Text style={styles.guidanceTitle}>Call emergency services directly</Text>
          <Text style={styles.guidanceBody}>
            {guidance ||
              "If you may be having a heart attack or stroke, call your local emergency services number immediately. Do not wait for this app."}
          </Text>
        </View>

        {!enabled ? (
          <View style={styles.card}>
            <Text style={styles.disabledTitle}>Emergency dispatch is off</Text>
            <Text style={styles.body}>
              This optional feature is disabled. Enable it in Settings to use app-assisted dispatch.
              The static guidance above always applies.
            </Text>
          </View>
        ) : location.loading || evaluate.isPending ? (
          <ActivityIndicator color={theme.colors.accent} style={styles.loader} />
        ) : decision ? (
          <DecisionPreview
            decision={decision}
            approximate={location.approximate}
            onStart={() => setConfirming(true)}
          />
        ) : (
          <View style={styles.card}>
            <Text style={styles.body}>
              No dispatch is recommended for the current state. The guidance above still applies.
            </Text>
          </View>
        )}

        {lastResult ? (
          <View style={styles.resultCard}>
            <Text style={styles.resultText}>{lastResult}</Text>
          </View>
        ) : null}

        <Text style={styles.h2}>Dispatch history</Text>
        {history.isLoading ? (
          <ActivityIndicator color={theme.colors.accent} />
        ) : (
          <DispatchHistoryList events={history.data?.events ?? []} />
        )}
      </ScrollView>

      {decision ? (
        <EmergencyConfirmDialog
          visible={confirming}
          recipientName={decision.recipient.name}
          channel={decision.channel}
          onConfirm={onConfirm}
          onCancel={() => setConfirming(false)}
          busy={dispatch.isPending}
        />
      ) : null}
    </SafeAreaView>
  );
}

function DecisionPreview({
  decision,
  approximate,
  onStart,
}: {
  decision: EmergencyDecision;
  approximate: boolean;
  onStart: () => void;
}) {
  const { recipient, routingReason, payload, channel } = decision;
  return (
    <View style={styles.card}>
      <View style={styles.row}>
        <Text style={styles.cardTitle}>Would contact</Text>
        <SimulatedDispatchBadge channel={channel} />
      </View>
      <Text style={styles.recipient}>{recipient.name}</Text>
      <Text style={styles.body}>
        {[recipient.kind, recipient.specialty].filter(Boolean).join(" · ")}
      </Text>
      <Text style={styles.meta}>
        Routing: {routingReason === "preferred_doctor_reachable" ? "preferred doctor (reachable)" : "nearest capable hospital"}
      </Text>

      <Text style={styles.sectionLabel}>Payload preview</Text>
      <Text style={styles.meta}>Patient: {payload.patient.name ?? "—"} · {payload.patient.phone ?? "—"}</Text>
      <Text style={styles.meta}>
        Location: {payload.location.lat.toFixed(4)}, {payload.location.lon.toFixed(4)}
        {approximate || payload.location.approximate ? " (approximate)" : ""}
      </Text>
      <Text style={styles.meta}>Emergency contacts: {payload.emergencyContacts.length}</Text>
      <Text style={styles.summary}>{payload.findingSummary}</Text>

      <Pressable style={styles.startBtn} onPress={onStart} accessibilityRole="button">
        <Text style={styles.startText}>Start dispatch…</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.bg },
  content: { padding: theme.spacing(4), gap: theme.spacing(3) },
  h1: { color: theme.colors.textPrimary, fontSize: theme.font.h1, fontWeight: "700" },
  h2: { color: theme.colors.textPrimary, fontSize: theme.font.h2, fontWeight: "700", marginTop: theme.spacing(2) },
  notice: { color: theme.colors.experimental, fontSize: theme.font.caption, fontWeight: "600" },
  guidanceCard: {
    backgroundColor: theme.colors.surfaceAlt,
    borderLeftWidth: 4,
    borderLeftColor: theme.colors.danger,
    borderRadius: theme.radius.md,
    padding: theme.spacing(3),
    gap: theme.spacing(1),
  },
  guidanceTitle: { color: theme.colors.danger, fontSize: theme.font.body, fontWeight: "700" },
  guidanceBody: { color: theme.colors.textPrimary, fontSize: theme.font.body, lineHeight: 20 },
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing(3),
    gap: theme.spacing(1),
  },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  cardTitle: { color: theme.colors.textSecondary, fontSize: theme.font.caption, textTransform: "uppercase" },
  recipient: { color: theme.colors.textPrimary, fontSize: theme.font.h2, fontWeight: "700" },
  disabledTitle: { color: theme.colors.warn, fontSize: theme.font.body, fontWeight: "700" },
  body: { color: theme.colors.textSecondary, fontSize: theme.font.body, lineHeight: 20 },
  meta: { color: theme.colors.textSecondary, fontSize: theme.font.caption },
  sectionLabel: {
    color: theme.colors.textPrimary,
    fontSize: theme.font.caption,
    fontWeight: "700",
    marginTop: theme.spacing(2),
    textTransform: "uppercase",
  },
  summary: { color: theme.colors.experimental, fontSize: theme.font.caption, marginTop: theme.spacing(1), lineHeight: 18 },
  startBtn: {
    backgroundColor: theme.colors.danger,
    borderRadius: theme.radius.md,
    paddingVertical: theme.spacing(3),
    alignItems: "center",
    marginTop: theme.spacing(2),
  },
  startText: { color: theme.colors.bg, fontSize: theme.font.body, fontWeight: "700" },
  loader: { marginVertical: theme.spacing(4) },
  resultCard: {
    backgroundColor: theme.colors.surfaceAlt,
    borderRadius: theme.radius.md,
    padding: theme.spacing(3),
  },
  resultText: { color: theme.colors.textPrimary, fontSize: theme.font.body },
});
