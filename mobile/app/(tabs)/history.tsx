import { StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { theme } from "@/theme";

/** History screen placeholder — filled in by Task 16 (Owner: Helenawai). */
export default function HistoryScreen() {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <Text style={styles.h1}>History</Text>
        <Text style={styles.body}>
          Daily/weekly/monthly trends, baseline overlay, anomaly markers, and past alerts land
          here (Task 16).
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
