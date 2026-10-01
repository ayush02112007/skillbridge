/**
 * Keyboard and screen-reader basics on the pages people live in.
 *
 * Not a full audit — these are the failures that make a page unusable rather
 * than merely imperfect: no skip link, focus lost inside a dialog, images and
 * controls with no accessible name.
 */
import { expect, test } from "@playwright/test";

import { DEMO, DEMO_PASSWORD, login } from "./helpers";

test("the landing page offers a skip link as the first tab stop", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  const focused = await page.evaluate(() => {
    const element = document.activeElement as HTMLElement | null;
    return { text: element?.textContent?.trim() ?? "", href: element?.getAttribute("href") ?? "" };
  });
  expect(`${focused.text} ${focused.href}`.toLowerCase()).toContain("main");
});

test("every image and icon-only control has an accessible name", async ({ page }) => {
  await login(page, DEMO.student, DEMO_PASSWORD);
  await page.goto("/student/dashboard");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  const unnamed = await page.evaluate(() => {
    const problems: string[] = [];
    for (const img of Array.from(document.querySelectorAll("img"))) {
      if (!img.getAttribute("alt") && img.getAttribute("aria-hidden") !== "true") {
        problems.push(`img ${img.getAttribute("src")?.slice(0, 40)}`);
      }
    }
    for (const button of Array.from(document.querySelectorAll("button"))) {
      const name =
        button.textContent?.trim() ||
        button.getAttribute("aria-label") ||
        button.getAttribute("title");
      if (!name) problems.push(`button ${button.className.slice(0, 40)}`);
    }
    return problems;
  });
  expect(unnamed, unnamed.join("\n")).toEqual([]);
});

test("a dialog traps focus and closes on Escape", async ({ page }) => {
  await login(page, DEMO.student, DEMO_PASSWORD);
  await page.goto("/opportunities");
  await page.locator('a[href^="/opportunities/"]').first().click();
  await page.waitForURL(/\/opportunities\/[0-9a-f-]+/);

  const apply = page.getByRole("button", { name: /^apply now$/i });
  if (!(await apply.isEnabled().catch(() => false))) test.skip(true, "already applied or closed");
  await apply.click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();

  // Focus moves in on the next paint, so wait for it rather than sampling once.
  await expect
    .poll(() => dialog.evaluate((node) => node.contains(document.activeElement)), {
      timeout: 5_000,
    })
    .toBe(true);

  for (let index = 0; index < 12; index += 1) await page.keyboard.press("Tab");
  const insideAfter = await dialog.evaluate((node) => node.contains(document.activeElement));
  expect(insideAfter, "focus escaped the dialog").toBeTruthy();

  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
});

/**
 * Checked across several portals, because a heading outline is easy to get
 * right on the page you were looking at and wrong on the next one.
 */
for (const route of [
  "/student/dashboard",
  "/student/applications",
  "/student/skill-gap",
  "/opportunities",
]) {
  test(`headings on ${route} start at h1 and do not skip a level`, async ({ page }) => {
    await login(page, DEMO.student, DEMO_PASSWORD);
    await page.goto(route);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // Section headings arrive with the data, so wait for the skeletons to
    // clear first — otherwise this asserts against the loading state.
    await expect
      .poll(() => page.locator("main .animate-pulse").count(), { timeout: 20_000 })
      .toBe(0);

    const levels = await page
      .locator("main :is(h1, h2, h3, h4, h5, h6)")
      .evaluateAll((nodes) => nodes.map((node) => Number(node.tagName.slice(1))));

    // A page whose only heading is its title is fine — a list of cards does
    // not have to invent section headings. What must hold is that the outline
    // starts at h1 and never jumps a level.
    expect(levels[0], "the first heading in <main> should be the page h1").toBe(1);
    for (let index = 1; index < levels.length; index += 1) {
      expect(
        levels[index] - levels[index - 1],
        `heading level jumped from h${levels[index - 1]} to h${levels[index]}`,
      ).toBeLessThanOrEqual(1);
    }
  });
}
