import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

import { theme } from "@/theme";

const queryClient = new QueryClient();

/**
 * Root layout. Wraps the app in React Query and a dark stack navigator.
 * The disclaimer route is registered as a modal (Task 23 fills it in).
 */
export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: theme.colors.bg },
          headerTintColor: theme.colors.textPrimary,
          contentStyle: { backgroundColor: theme.colors.bg },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="disclaimer" options={{ presentation: "modal", title: "Disclaimer" }} />
        <Stack.Screen name="emergency" options={{ presentation: "modal", title: "Emergency" }} />
      </Stack>
    </QueryClientProvider>
  );
}
