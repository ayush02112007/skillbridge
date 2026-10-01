/**
 * Every public page answers, and every navigation target exists.
 *
 * A 404 behind a link in the navigation is the kind of thing that survives
 * code review and is obvious in a browser, so it is checked mechanically.
 */
import { expect, test } from "@playwright/test";

import { collectErrors, DEMO, DEMO_PASSWORD, login } from "./helpers";

test.describe("public pages", () => {
  test("the landing page renders and offers the primary routes", async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto("/");

    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByRole("link", { name: "Sign in" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /get started/i }).first()).toBeVisible();
    expect(errors, errors.join("\n")).toEqual([]);
  });

  test("opportunities can be browsed without an account", async ({ page }) => {
    await page.goto("/opportunities");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    // Seeded postings must actually appear; an empty marketplace would pass
    // a weaker assertion.
    await expect(page.locator('a[href^="/opportunities/"]').first())
      .toBeVisible({ timeout: 15_000 });
  });

  test("an opportunity detail page invites an anonymous visitor to sign in", async ({ page }) => {
    await page.goto("/opportunities");
    await page.locator('a[href^="/opportunities/"]').first().click();
    await page.waitForURL(/\/opportunities\/[0-9a-f-]+/);
    await expect(page.getByText(/sign in to see your match score/i)).toBeVisible();
  });

  test("an unknown page returns the not-found view, not a crash", async ({ page }) => {
    const response = await page.goto("/this-route-does-not-exist");
    expect(response?.status()).toBe(404);
  });
});

test.describe("authenticated navigation", () => {
  // Every link in a portal's sidebar must resolve to a real page.
  const portals = [
    { email: DEMO.student, home: "/student/dashboard" },
    { email: DEMO.industry, home: "/industry/dashboard" },
    { email: DEMO.faculty, home: "/academician/dashboard" },
    { email: DEMO.institution, home: "/institution/dashboard" },
    { email: DEMO.admin, home: "/admin/dashboard" },
  ];

  for (const portal of portals) {
    test(`${portal.home} — every sidebar link resolves`, async ({ page }) => {
      await login(page, portal.email, DEMO_PASSWORD);
      await expect(page).toHaveURL(new RegExp(portal.home));

      const hrefs = await page
        .getByRole("navigation", { name: "Main" })
        .getByRole("link")
        .evaluateAll((links) =>
          links.map((link) => (link as HTMLAnchorElement).getAttribute("href") ?? ""),
        );
      const routes = [...new Set(hrefs.filter((href) => href.startsWith("/")))];
      expect(routes.length).toBeGreaterThan(3);

      for (const route of routes) {
        const response = await page.goto(route);
        expect(response?.status(), `${route} returned ${response?.status()}`).toBeLessThan(400);
        await expect(
          page.getByRole("heading", { level: 1 }),
          `${route} rendered no page heading`,
        ).toBeVisible({ timeout: 20_000 });
      }
    });
  }
});
