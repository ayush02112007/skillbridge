/**
 * Phone layout.
 *
 * Students overwhelmingly use the platform on a phone, so the portals must be
 * usable at 412px: navigation reachable, no horizontal scroll, headings visible.
 * Runs under the `mobile` Playwright project only.
 */
import { expect, test } from "@playwright/test";

import { DEMO, DEMO_PASSWORD, login } from "./helpers";

test("the landing page fits the viewport", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, "the page scrolls sideways on a phone").toBeLessThanOrEqual(1);
});

test("the student portal navigation is reachable on a phone", async ({ page }) => {
  await login(page, DEMO.student, DEMO_PASSWORD);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  // The sidebar collapses behind a button at this width.
  const openNav = page.getByRole("button", { name: "Open navigation" });
  await expect(openNav).toBeVisible();
  await openNav.click();

  const nav = page.getByRole("navigation", { name: "Main" });
  await expect(nav).toBeVisible();
  await expect(nav.getByRole("link").first()).toBeVisible();

  await page.getByRole("button", { name: "Close navigation" }).click();
  await expect(page.getByRole("button", { name: "Open navigation" })).toBeVisible();
});

test("dashboard content does not overflow", async ({ page }) => {
  await login(page, DEMO.student, DEMO_PASSWORD);
  for (const route of ["/student/dashboard", "/student/skill-gap", "/student/applications"]) {
    await page.goto(route);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 20_000 });
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow, `${route} scrolls sideways on a phone`).toBeLessThanOrEqual(1);
  }
});
