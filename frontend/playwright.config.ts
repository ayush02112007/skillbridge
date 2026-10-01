import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end configuration.
 *
 * Both servers are started by Playwright so `npm run test:e2e` is a single
 * command from a clean checkout. The API runs against its own throwaway SQLite
 * database (see backend/scripts/e2e-backend.sh) — the suite registers users and
 * advances applications, which should never touch your development data.
 *
 * Locally, an already-running server is reused; in CI it never is.
 */
const BASE_URL = process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000";
const API_URL = process.env.E2E_API_URL ?? "http://127.0.0.1:8000";
const isCI = !!process.env.CI;

/**
 * Which browser binary to drive.
 *
 * By default Playwright uses the Chromium build it downloads itself, which is
 * what CI does. On a machine where that download is blocked, set
 * `E2E_BROWSER_CHANNEL=chrome` (or `msedge`) to drive the locally installed
 * browser instead — same engine, no download.
 */
const channel = process.env.E2E_BROWSER_CHANNEL || undefined;

/**
 * Video capture needs the ffmpeg binary that ships with Playwright's own
 * browser download. Driving a locally installed browser implies that download
 * was not done, so recording is turned off rather than failing every test on
 * a missing binary. Traces and screenshots still work and are the useful
 * artefacts anyway.
 */
const video = channel ? "off" : "retain-on-failure";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,       // the suite shares one seeded database
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: isCI
    ? [["github"], ["html", { open: "never" }], ["list"]]
    : [["list"], ["html", { open: "never" }]],

  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video,
    actionTimeout: 15_000,
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], channel },
      // responsive.spec.ts asserts the phone layout; running it at desktop
      // width asserts the opposite of what the page correctly does.
      testIgnore: /responsive\.spec\.ts/,
    },
    // Every portal is used on a phone; the layout is part of the contract.
    {
      name: "mobile",
      use: { ...devices["Pixel 7"], channel },
      testMatch: /responsive\.spec\.ts/,
    },
  ],

  webServer: [
    {
      command: "bash ../backend/scripts/e2e-backend.sh",
      url: `${API_URL}/health`,
      reuseExistingServer: !isCI,
      timeout: 180_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: `npm run start -- --port 3000`,
      url: BASE_URL,
      reuseExistingServer: !isCI,
      timeout: 180_000,
      env: { NEXT_PUBLIC_API_URL: API_URL },
    },
  ],
});
