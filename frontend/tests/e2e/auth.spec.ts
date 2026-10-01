/**
 * Registration, sign-in, route protection and password recovery.
 */
import { expect, test } from "@playwright/test";

import {
  DEMO, DEMO_PASSWORD, E2E_EMAIL_DOMAIN, login, STRONG_PASSWORD, uniqueEmail,
} from "./helpers";

test.describe("registration", () => {
  test("a student can create an account and lands in the student portal", async ({ page }) => {
    const email = uniqueEmail("student");
    await page.goto("/register");

    await page.getByLabel(/^Full name/).fill("E2E Test Student");
    await page.getByLabel(/^Email/).fill(email);
    await page.getByLabel(/^Password/).fill(STRONG_PASSWORD);
    await page.getByLabel(/accept the terms/i).check();
    await page.getByRole("button", { name: /create account/i }).click();

    await page.waitForURL(/\/student\//, { timeout: 30_000 });
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/welcome/i);
  });

  test("a weak password is rejected before it reaches the server", async ({ page }) => {
    await page.goto("/register");
    await page.getByLabel(/^Full name/).fill("E2E Weak Password");
    await page.getByLabel(/^Email/).fill(uniqueEmail("weak"));
    await page.getByLabel(/^Password/).fill("password");
    await page.getByLabel(/accept the terms/i).check();
    await page.getByRole("button", { name: /create account/i }).click();

    await expect(page.getByText(/at least 10 characters|include an uppercase/i).first())
      .toBeVisible();
    await expect(page).toHaveURL(/\/register/);
  });

  test("a duplicate email is reported, not silently accepted", async ({ page }) => {
    await page.goto("/register");
    await page.getByLabel(/^Full name/).fill("Duplicate Demo");
    await page.getByLabel(/^Email/).fill(DEMO.student);
    await page.getByLabel(/^Password/).fill(STRONG_PASSWORD);
    await page.getByLabel(/accept the terms/i).check();
    await page.getByRole("button", { name: /create account/i }).click();

    await expect(page.getByRole("alert").first()).toBeVisible({ timeout: 15_000 });
    await expect(page).toHaveURL(/\/register/);
  });
});

test.describe("sign in", () => {
  test("wrong credentials produce an error and no session", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/^Email/).fill(DEMO.student);
    await page.getByLabel(/^Password/).fill("definitely-not-the-password");
    await page.getByRole("button", { name: "Sign in", exact: true }).click();

    await expect(page.getByRole("alert").first()).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });

  test("each role is sent to its own portal", async ({ page }) => {
    const expectations: [string, RegExp][] = [
      [DEMO.student, /\/student\/dashboard/],
      [DEMO.industry, /\/industry\/dashboard/],
      [DEMO.faculty, /\/academician\/dashboard/],
      [DEMO.institution, /\/institution\/dashboard/],
      [DEMO.admin, /\/admin\/dashboard/],
    ];

    for (const [email, url] of expectations) {
      await page.context().clearCookies();
      await page.goto("/login");
      await page.evaluate(() => window.localStorage.clear());
      await login(page, email, DEMO_PASSWORD);
      await expect(page, `${email} should land on ${url}`).toHaveURL(url);
    }
  });

  test("a demo account button fills the form", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: /^Student/ }).click();
    await expect(page.getByLabel(/^Email/)).toHaveValue(DEMO.student);
    await expect(page.getByLabel(/^Password/)).not.toHaveValue("");
  });
});

test.describe("route protection", () => {
  test("an anonymous visitor is redirected away from a portal page", async ({ page }) => {
    await page.goto("/student/dashboard");
    await page.waitForURL(/\/login/, { timeout: 20_000 });
    // The destination is preserved so the visitor is not dumped on a dashboard
    // they did not ask for.
    expect(page.url()).toContain("next=");
  });

  test("a student cannot open the recruiter portal", async ({ page }) => {
    await login(page, DEMO.student, DEMO_PASSWORD);
    await page.goto("/industry/applicants");
    // Either bounced back to their own portal, or told plainly.
    await expect(async () => {
      const url = page.url();
      const denied = await page.getByText(/don't have access|not authorised|not authorized|permission/i).count();
      expect(url.includes("/industry/applicants") === false || denied > 0).toBeTruthy();
    }).toPass({ timeout: 20_000 });
  });

  test("signing out clears the session and protects the portal again", async ({ page }) => {
    await login(page, DEMO.student, DEMO_PASSWORD);
    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("button", { name: "Sign out" }).click();
    await page.waitForURL(/\/login(\?|$)/, { timeout: 20_000 });

    await page.goto("/student/dashboard");
    await page.waitForURL(/\/login/, { timeout: 20_000 });
  });
});

test.describe("password recovery", () => {
  test("the forgot-password link from the sign-in page works", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("link", { name: /forgot password/i }).click();
    await page.waitForURL(/\/forgot-password/);
    await expect(page.getByRole("heading", { name: /reset your password/i })).toBeVisible();
  });

  test("the response is identical for registered and unknown addresses", async ({ page }) => {
    for (const email of [DEMO.student, `nobody.${Date.now()}@${E2E_EMAIL_DOMAIN}`]) {
      await page.goto("/forgot-password");
      await page.getByLabel(/^Email/).fill(email);
      await page.getByRole("button", { name: /send reset link/i }).click();
      // Account enumeration must not be possible from this screen.
      await expect(page.getByRole("heading", { name: /check your inbox/i })).toBeVisible();
    }
  });

  test("a reset link without a token explains itself instead of erroring", async ({ page }) => {
    await page.goto("/reset-password");
    await expect(page.getByRole("heading", { name: /link is incomplete/i })).toBeVisible();
  });

  test("an invalid verification token is reported clearly", async ({ page }) => {
    await page.goto("/verify-email?token=not-a-real-token-at-all");
    await expect(page.getByRole("heading", { name: /could not verify/i })).toBeVisible({
      timeout: 20_000,
    });
  });
});
