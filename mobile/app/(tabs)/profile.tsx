import { StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { theme } from "@/theme";

/** Settings / Care-profile screen placeholder — filled in by Task 22 (Owner: Helenawai). */
export default function ProfileScreen() {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <Text style={styles.h1}>Settings</Text>
        <Text style={styles.body}>
          Care profile, optional emergency contacts, preferred doctor, and feature toggles
          (warnings / suggestions / emergency — suggestions and emergency default OFF) land here
          (Task 22). The experimental disclaimer is reachable from here (Task 23).
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
