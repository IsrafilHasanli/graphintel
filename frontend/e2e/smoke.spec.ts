import { test, expect } from "@playwright/test";

/**
 * Smoke test. Requires the frontend running (npm run dev / start) and, for
 * live data, the FastAPI backend at NEXT_PUBLIC_API_BASE. The assertions here
 * target the app shell + navigation so they pass even before data is seeded.
 */

test("dashboard loads with primary navigation", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /operations dashboard/i }),
  ).toBeVisible();
  await expect(page.getByRole("navigation", { name: /primary/i })).toBeVisible();
  await expect(
    page.getByRole("button", { name: /seed demo data/i }),
  ).toBeVisible();
});

test("navigate to the Ask screen and see golden questions", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Ask", exact: true }).click();
  await expect(page).toHaveURL(/\/ask$/);
  await expect(
    page.getByRole("heading", { name: /ask an operational question/i }),
  ).toBeVisible();
  // At least one golden question chip should be present.
  await expect(
    page.getByRole("button", { name: /which engineering team owns/i }),
  ).toBeVisible();
});

test("graph explorer route renders", async ({ page }) => {
  await page.goto("/graph");
  await expect(
    page.getByRole("heading", { name: /graph explorer/i }).first(),
  ).toBeVisible();
});
