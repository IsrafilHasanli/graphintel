import { defineConfig, devices } from "@playwright/test";

/**
 * E2E smoke tests. These run against a live frontend (which itself proxies to
 * the FastAPI backend at NEXT_PUBLIC_API_BASE). Start `npm run dev` (or
 * `npm run build && npm run start`) plus the backend before running.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
