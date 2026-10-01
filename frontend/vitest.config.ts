import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./", import.meta.url)) },
  },
  test: {
    environment: "jsdom",
    // An origin is required for localStorage and for the URL parsing the
    // API client does when it builds request URLs.
    environmentOptions: { jsdom: { url: "http://localhost:3000" } },
    globals: true,
    setupFiles: ["./tests/unit/setup.ts"],
    // Playwright specs live in tests/e2e and are run by `npm run test:e2e`.
    include: ["tests/unit/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      // Feature screens are exercised by the Playwright suite against a real
      // API; counting them here would only report a misleading zero.
      include: ["lib/**", "components/ui/**"],
      exclude: ["lib/query.tsx"],
      thresholds: { lines: 90, functions: 85, branches: 85 },
    },
  },
});
