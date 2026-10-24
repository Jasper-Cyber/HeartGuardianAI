import { StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { theme } from "@/theme";

/** Simulator screen placeholder — filled in by Task 17 (Owner: Helenawai). */
export default function SimulatorScreen() {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <Text style={styles.h1}>Simulator</Text>
        <Text style={styles.body}>
          Scenario picker (A/B/C) and Start / Pause / Reset controls land here (Task 17).
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
