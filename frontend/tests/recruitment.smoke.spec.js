import { expect, test } from "@playwright/test";

test("user can sign in and open live dashboard", async ({ page }) => {
  await page.goto("/");
  await page.getByPlaceholder("Username").fill(process.env.RMS_E2E_USER || "admin");
  await page.getByPlaceholder("Password").fill(process.env.RMS_E2E_PASSWORD || "ChangeMe!2026");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Good morning, team." })).toBeVisible();
  for (const label of [
    "Total candidates",
    "Active requisitions",
    "Total applications",
    "Interviews scheduled",
    "Offers released",
    "Hiring conversion",
  ]) {
    const card = page.getByText(label, { exact: true }).locator("..");
    await expect(card).toBeVisible();
    await expect(card.getByText(/^(0|0%)$/, { exact: true })).toBeVisible();
  }
  await expect(page.getByText("0 total", { exact: true })).toBeVisible();
});

test("user can navigate to interview scheduling", async ({ page }) => {
  await page.goto("/");
  await page.getByPlaceholder("Username").fill(process.env.RMS_E2E_USER || "admin");
  await page.getByPlaceholder("Password").fill(process.env.RMS_E2E_PASSWORD || "ChangeMe!2026");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("link", { name: "Interviews" }).click();
  await expect(page.getByRole("heading", { name: "Interview calendar" })).toBeVisible();
  await expect(page.getByText("Schedule, inspect availability, and resolve conflicts")).toBeVisible();
});
