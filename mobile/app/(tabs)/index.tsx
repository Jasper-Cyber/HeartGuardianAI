import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { SimulatedDataRibbon } from "@/components/SimulatedDataRibbon";
import { theme } from "@/theme";

/** Dashboard screen placeholder — filled in by Task 14 (Owner: Helenawai). */
export default function DashboardScreen() {
  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <SimulatedDataRibbon />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.h1}>HeartGuardian AI</Text>
        <Text style={styles.sub}>Dashboard</Text>
        <View style={styles.card}>
          <Text style={styles.body}>
            Metric cards, activity/sleep, monitoring status, and trend charts land here (Task 14).
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.bg },
  content: { padding: theme.spacing(4), gap: theme.spacing(3) },
  h1: { color: theme.colors.textPrimary, fontSize: theme.font.h1, fontWeight: "700" },
  sub: { color: theme.colors.textSecondary, fontSize: theme.font.h2 },
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing(4),
  },
  body: { color: theme.colors.textPrimary, fontSize: theme.font.body },
});
