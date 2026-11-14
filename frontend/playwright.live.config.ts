import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./live",
  workers: 1,
  timeout: 360_000,
  use: {
    ...devices["Desktop Chrome"],
    baseURL: process.env.LIVE_FRONTEND_URL ?? "http://127.0.0.1:3111",
    trace: "off",
  },
  reporter: "list",
});
