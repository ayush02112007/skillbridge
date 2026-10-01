/**
 * Theme switching in a real browser.
 *
 * The unit tests cover the provider's logic. These cover what only a browser
 * can show: that the pre-paint script actually beats the first paint, that the
 * choice survives a reload and a navigation, and that the toggle is present
 * and effective on every kind of surface — public, auth and portal.
 */
import { expect, test, type Page } from "@playwright/test";

import { DEMO, DEMO_PASSWORD, login } from "./helpers";

const THEME_KEY = "sb.theme";

async function resolvedTheme(page: Page): Promise<"light" | "dark"> {
  return page.evaluate(() =>
    document.documentElement.classList.contains("dark") ? "dark" : "light",
  );
}

/** The page background actually painted, not just the class on <html>. */
async function bodyBackground(page: Page): Promise<string> {
  return page.evaluate(() => getComputedStyle(document.body).backgroundColor);
}

test.describe("the toggle", () => {
  test("is on the marketing page and switches the painted colours", async ({ page }) => {
    await page.goto("/");
    const before = await resolvedTheme(page);
    const backgroundBefore = await bodyBackground(page);

    const toggle = page.getByRole("button", { name: /switch to (light|dark) theme/i }).first();
    await expect(toggle).toBeVisible();
    await toggle.click();

    await expect.poll(() => resolvedTheme(page)).not.toBe(before);
    expect(await bodyBackground(page)).not.toBe(backgroundBefore);
  });

  test("is on the sign-in page", async ({ page }) => {
    await page.goto("/login");
    const toggle = page.getByRole("button", { name: /switch to (light|dark) theme/i });
    await expect(toggle).toBeVisible();

    const before = await resolvedTheme(page);
    await toggle.click();
    await expect.poll(() => resolvedTheme(page)).not.toBe(before);
  });

  test("is in the portal header, and the choice follows the user across pages", async ({ page }) => {
    await login(page, DEMO.student, DEMO_PASSWORD);

    const toggle = page.getByRole("button", { name: /switch to (light|dark) theme/i });
    await expect(toggle).toBeVisible();
    await toggle.click();
    const chosen = await resolvedTheme(page);

    for (const route of ["/student/skill-gap", "/student/applications", "/opportunities"]) {
      await page.goto(route);
      expect(await resolvedTheme(page), `${route} lost the theme`).toBe(chosen);
    }
  });
});

test.describe("persistence", () => {
  test("survives a reload, and is applied before React hydrates", async ({ browser }) => {
    // A light system preference, so a wrong implementation would paint light
    // first and only correct itself once React ran.
    const context = await browser.newContext({ colorScheme: "light" });
    const page = await context.newPage();

    await page.goto("/");
    await page.evaluate((key) => localStorage.setItem(key, "dark"), THEME_KEY);

    await page.goto("/student/dashboard", { waitUntil: "domcontentloaded" });

    const early = await page.evaluate(() => ({
      className: document.documentElement.className,
      colorScheme: document.documentElement.style.colorScheme,
      background: getComputedStyle(document.body).backgroundColor,
      /**
       * The structural half of the claim: a *blocking* inline script in
       * <head> that reads the stored choice. Asserting this rather than
       * racing readyState — the page can finish loading before a probe runs,
       * which says nothing about when the class was applied.
       */
      blockingScriptInHead: [...document.head.querySelectorAll("script")].some(
        (node) =>
          !node.src &&
          !node.async &&
          !node.defer &&
          node.textContent?.includes("sb.theme"),
      ),
    }));

    expect(early.blockingScriptInHead, "no blocking theme script in <head>").toBe(true);
    expect(early.className, "the dark class was not applied before hydration")
      .toContain("dark");
    expect(early.colorScheme).toBe("dark");
    // The painted background is the part a user would actually see flash.
    expect(early.background).not.toBe("rgb(255, 255, 255)");

    await page.waitForLoadState("load");
    expect(await resolvedTheme(page), "the theme changed after hydration").toBe("dark");

    await context.close();
  });

  test("a stored light choice wins over a dark system preference", async ({ browser }) => {
    const context = await browser.newContext({ colorScheme: "dark" });
    const page = await context.newPage();

    await page.goto("/");
    await page.evaluate((key) => localStorage.setItem(key, "light"), THEME_KEY);
    await page.reload();

    expect(await resolvedTheme(page)).toBe("light");
    await context.close();
  });
});

test.describe("system preference", () => {
  test("is the default when nothing has been chosen", async ({ browser }) => {
    for (const scheme of ["dark", "light"] as const) {
      const context = await browser.newContext({ colorScheme: scheme });
      const page = await context.newPage();
      await page.goto("/");
      expect(await resolvedTheme(page), `system ${scheme} was not followed`).toBe(scheme);
      await context.close();
    }
  });
});

test.describe("both themes render", () => {
  // A theme that only works on the page you built it on is not a theme.
  const routes = [
    "/", "/login", "/opportunities",
    "/student/dashboard", "/student/skill-gap", "/student/applications",
    "/industry/applicants", "/admin/dashboard",
  ];

  for (const scheme of ["light", "dark"] as const) {
    test(`${scheme}: every surface paints and stays readable`, async ({ browser }) => {
      const context = await browser.newContext({ colorScheme: scheme });
      const page = await context.newPage();
      await login(page, DEMO.admin, DEMO_PASSWORD);

      for (const route of routes) {
        await page.goto(route);
        await expect(page.getByRole("heading", { level: 1 }).first())
          .toBeVisible({ timeout: 20_000 });
        expect(await resolvedTheme(page), `${route} ignored the ${scheme} scheme`)
          .toBe(scheme);

        // The page must not be painting light text on a light background, or
        // the reverse — which is what a missed token looks like.
        const contrastOk = await page.evaluate(() => {
          const luminance = (colour: string) => {
            const [r, g, b] = (colour.match(/[\d.]+/g) ?? ["255", "255", "255"])
              .slice(0, 3)
              .map(Number)
              .map((c) => {
                const v = c / 255;
                return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
              });
            return 0.2126 * r + 0.7152 * g + 0.0722 * b;
          };
          const body = getComputedStyle(document.body);
          const heading = document.querySelector("main h1");
          if (!heading) return true;
          const text = luminance(getComputedStyle(heading).color);
          const background = luminance(body.backgroundColor);
          const ratio =
            (Math.max(text, background) + 0.05) / (Math.min(text, background) + 0.05);
          return ratio >= 4.5;
        });
        expect(contrastOk, `${route} in ${scheme}: heading contrast below 4.5:1`).toBe(true);
      }
      await context.close();
    });
  }
});
