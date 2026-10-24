import { StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { theme } from "@/theme";

/** Insights/Alerts screen placeholder — filled in by Task 15 (Owner: Helenawai). */
export default function InsightsScreen() {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <Text style={styles.h1}>Insights</Text>
        <Text style={styles.body}>
          Alert state banner, explanation, next steps, and the always-visible emergency guidance
          card land here (Task 15). Alerts are experimental and do not replace medical evaluation.
        </Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.bg },
  content: { padding: theme.spacing(4), gap: theme.spacing(3) },
  h1: { color: theme.colors.textPrimary, fontSize: theme.font.h1, fontWeight: "700" },
  body: { color: theme.colors.textSecondary, fontSize: theme.font.body },
});
