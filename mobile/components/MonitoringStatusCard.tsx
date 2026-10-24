import { StyleSheet, Text, View } from "react-native";

import type { AlertState } from "@/api/types";
import { theme } from "@/theme";

interface MonitoringStatusCardProps {
  state: AlertState;
  /** Optional short title from the current alert; falls back to a default. */
  title?: string;
}

const STATE_META: Record<
  AlertState,
  { label: string; color: string; defaultTitle: string }
> = {
  normal: {
    label: "Normal monitoring",
    color: theme.colors.accentGreen,
    defaultTitle: "Everything looks steady",
  },
  trend_review: {
    label: "Trend review recommended",
    color: theme.colors.warn,
    defaultTitle: "A trend may be worth reviewing",
  },
  attention: {
    label: "Needs further assessment",
    color: theme.colors.danger,
    defaultTitle: "A measurement may need attention",
  },
};

/**
 * Personalized monitoring-status banner on the dashboard (Req 1.4), colored by
 * the current alert state. Non-diagnostic wording only.
 */
export function MonitoringStatusCard({ state, title }: MonitoringStatusCardProps) {
  const meta = STATE_META[state];
  return (
    <View
      style={[styles.card, { borderLeftColor: meta.color }]}
      accessibilityRole="summary"
      accessibilityLabel={`Monitoring status: ${meta.label}`}
    >
      <View style={styles.row}>
        <View style={[styles.dot, { backgroundColor: meta.color }]} />
        <Text style={[styles.status, { color: meta.color }]}>{meta.label}</Text>
      </View>
      <Text style={styles.title}>{title ?? meta.defaultTitle}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderLeftWidth: 4,
    padding: theme.spacing(4),
    gap: theme.spacing(1),
  },
  row: { flexDirection: "row", alignItems: "center", gap: theme.spacing(2) },
  dot: { width: 10, height: 10, borderRadius: 5 },
  status: { fontSize: theme.font.caption, fontWeight: "700", textTransform: "uppercase", letterSpacing: 0.5 },
  title: { color: theme.colors.textPrimary, fontSize: theme.font.body },
});
