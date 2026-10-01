/** Shared helpers for the end-to-end suite. */
import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const DEMO_PASSWORD = process.env.E2E_DEMO_PASSWORD ?? "DemoPass!2024";

export const DEMO = {
  student: "student@demo.com",
  industry: "industry-admin@demo.com",
  faculty: "faculty@demo.com",
  institution: "institution@demo.com",
  admin: "admin@demo.com",
} as const;

/**
 * Domain for generated addresses.
 *
 * Not `.test`: RFC 2606 reserves it, and the email validator rejects reserved
 * and special-use domains — correctly, since they can never receive mail. A
 * fixture using one could never register.
 */
export const E2E_EMAIL_DOMAIN = "e2etest.dev";

/** An address that cannot collide with a previous run's registrations. */
export function uniqueEmail(prefix = "e2e"): string {
  return `${prefix}.${Date.now()}.${Math.floor(Math.random() * 1e4)}@${E2E_EMAIL_DOMAIN}`;
}

/** A password that satisfies the server-side policy. */
export const STRONG_PASSWORD = "E2ePassw0rd!check";

export async function login(page: Page, email: string, password = DEMO_PASSWORD) {
  await page.goto("/login");
  await page.getByLabel(/^Email/).fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  // The router pushes to the role's home route once the session is established.
  await page.waitForURL((url) => !url.pathname.startsWith("/login"), { timeout: 20_000 });
}

export async function logout(page: Page) {
  await page.getByRole("button", { name: "Account menu" }).click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.waitForURL(/\/login(\?|$)/, { timeout: 20_000 });
}

/**
 * Collects page errors and console errors so a test can assert the page is
 * not merely *rendering* but rendering without blowing up. Next.js emits some
 * noise of its own, which is filtered out.
 */
export function collectErrors(page: Page): string[] {
  const errors: string[] = [];
  const ignore = [
    /Download the React DevTools/i,
    /\[Fast Refresh\]/i,
    /hydrat/i, // dev-only hydration diffs from date formatting
    /favicon/i,
  ];
  page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() !== "error") return;
    const text = message.text();
    if (ignore.some((pattern) => pattern.test(text))) return;
    errors.push(`console: ${text}`);
  });
  return errors;
}

/** Assert the page rendered a real view rather than an error boundary. */
export async function expectNoErrorState(page: Page) {
  await expect(page.getByText("We could not load this")).toHaveCount(0);
  await expect(page.getByText(/Application error|500 Internal/i)).toHaveCount(0);
}

export const API_URL = process.env.E2E_API_URL ?? "http://127.0.0.1:8000";

/**
 * A posting owned by the demo recruiter's company.
 *
 * The journey has the student apply through the UI and the recruiter review
 * it — which only works if the posting belongs to *that* recruiter's company.
 * Picking whatever happens to be first in the public list is a coin flip
 * across ten seeded companies, so the posting is resolved up front through
 * the API. Setup through the API, behaviour through the UI.
 */
export async function recruiterOwnedInternship(
  request: APIRequestContext,
): Promise<{ id: string; title: string }> {
  const auth = await request.post(`${API_URL}/api/v1/auth/login`, {
    data: { email: DEMO.industry, password: DEMO_PASSWORD },
  });
  expect(auth.ok(), `recruiter login failed: ${auth.status()}`).toBeTruthy();
  const token = (await auth.json()).data.tokens.access_token as string;

  const listed = await request.get(
    `${API_URL}/api/v1/internships/mine?page_size=20`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  expect(listed.ok(), `listing the recruiter's internships failed: ${listed.status()}`)
    .toBeTruthy();

  const rows = (await listed.json()).data as {
    id: string; title: string; status: string; is_open?: boolean;
  }[];
  const open = rows.find((row) => row.status === "PUBLISHED" && row.is_open !== false)
    ?? rows[0];
  expect(open, "the demo recruiter's company has no internship to apply to").toBeTruthy();
  return { id: open.id, title: open.title };
}
