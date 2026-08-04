import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev -- --hostname 127.0.0.1",
    url: "http://127.0.0.1:3000",
    // The CI workflow starts and health-checks the frontend before invoking
    // Playwright, so reuse that server instead of trying to bind port 3000 a
    // second time. This also keeps local runs convenient when the app is open.
    reuseExistingServer: true,
    timeout: 45_000,
  },
});
