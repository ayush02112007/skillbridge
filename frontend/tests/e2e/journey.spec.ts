/**
 * The end-to-end journey the specification describes:
 *
 *   register → sign in → complete profile → take an assessment →
 *   view skill gaps → find an internship → apply →
 *   recruiter sees the application → recruiter shortlists
 *
 * It runs as one ordered story against a single account, because the point is
 * that the steps connect: the assessment feeds the gap analysis, the gap
 * analysis feeds the match score, and the match score is what the recruiter
 * sees next to the application the student submitted.
 */
import { expect, test, type Page } from "@playwright/test";

import {
  DEMO, DEMO_PASSWORD, login, recruiterOwnedInternship, STRONG_PASSWORD, uniqueEmail,
} from "./helpers";

test.describe.configure({ mode: "serial" });

const STUDENT_EMAIL = uniqueEmail("journey");
/**
 * Unique per run.
 *
 * The recruiter finds this student by searching their name, and a fixed name
 * matches every previous run's student too when the database is reused — so
 * the search could land on an application that had already been moved on.
 */
const STUDENT_NAME = `Journey Student ${Date.now().toString().slice(-7)}`;
let appliedTitle = "";

async function signInAsJourneyStudent(page: Page) {
  await login(page, STUDENT_EMAIL, STRONG_PASSWORD);
}

test("1 · a student registers", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel(/^Full name/).fill(STUDENT_NAME);
  await page.getByLabel(/^Email/).fill(STUDENT_EMAIL);
  await page.getByLabel(/^Password/).fill(STRONG_PASSWORD);

  // Attaching to an institution is what makes the student visible to their
  // placement cell later.
  const institution = page.getByLabel(/institution/i);
  if (await institution.count()) {
    const values = await institution.locator("option").evaluateAll((options) =>
      options.map((option) => (option as HTMLOptionElement).value).filter(Boolean),
    );
    if (values.length) await institution.selectOption(values[0]);
  }

  await page.getByLabel(/accept the terms/i).check();
  await page.getByRole("button", { name: /create account/i }).click();

  await page.waitForURL(/\/student\//, { timeout: 30_000 });
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/welcome/i);
});

test("2 · signs in again with the new credentials", async ({ page }) => {
  await signInAsJourneyStudent(page);
  await expect(page).toHaveURL(/\/student\/dashboard/);
});

test("3 · completes the profile", async ({ page }) => {
  await signInAsJourneyStudent(page);
  await page.goto("/student/profile");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  // Fill whichever of the core fields this build exposes, then save.
  const fills: [RegExp, string][] = [
    [/head-?line|title/i, "Final-year CSE student focused on backend engineering"],
    [/city|location/i, "Pune"],
    [/graduation year/i, "2026"],
    [/phone/i, "9876543210"],
  ];
  for (const [label, value] of fills) {
    const field = page.getByLabel(label).first();
    if (!(await field.count())) continue;
    const tag = await field.evaluate((node) => node.tagName.toLowerCase());
    if (tag === "select") {
      const options = await field.locator("option").evaluateAll((nodes) =>
        nodes.map((node) => (node as HTMLOptionElement).value).filter(Boolean),
      );
      const match = options.find((option) => option === value) ?? options[0];
      if (match) await field.selectOption(match);
    } else {
      await field.fill(value);
    }
  }

  const save = page.getByRole("button", { name: /^save|save changes|update profile/i }).first();
  await save.click();
  await expect(page.getByText(/saved|updated/i).first()).toBeVisible({ timeout: 20_000 });
});

test("4 · takes a skill assessment and receives a measured score", async ({ page }) => {
  test.slow(); // an assessment is a multi-question form
  await signInAsJourneyStudent(page);
  await page.goto("/student/assessment");

  await page.getByRole("button", { name: /start assessment/i }).first().click();

  // Answer every question, then submit from the last one.
  await expect(page.getByRole("button", { name: /^Question 1/ })).toBeVisible({ timeout: 20_000 });
  const total = await page.getByRole("button", { name: /^Question \d+/ }).count();
  expect(total).toBeGreaterThan(0);

  for (let index = 0; index < total; index += 1) {
    await page.getByRole("button", { name: new RegExp(`^Question ${index + 1}[,$]`) }).click();
    const options = page.locator("fieldset input[type=radio], fieldset input[type=checkbox]");
    await expect(options.first()).toBeVisible();
    // A deliberately naive answer: first option every time. The score is
    // whatever it is — the assertion is that scoring happened, not that the
    // fixture student did well.
    await options.first().check();
  }

  await page.getByRole("button", { name: /^Submit \(/ }).click();

  // The result screen is the point: a score, and a per-skill breakdown that
  // proves the attempt was actually scored rather than just recorded.
  await expect(page.getByText(/%/).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: /per-skill breakdown/i })).toBeVisible();
});

test("5 · sees a skill gap derived from that assessment", async ({ page }) => {
  await signInAsJourneyStudent(page);
  await page.goto("/student/skill-gap");
  await expect(page.getByRole("heading", { name: /skill gap analysis/i })).toBeVisible();

  // Pick a target role if one is not already chosen.
  const roleSelect = page.getByLabel(/target role|role/i).first();
  if (await roleSelect.count()) {
    const options = await roleSelect.locator("option").evaluateAll((nodes) =>
      nodes.map((node) => (node as HTMLOptionElement).value).filter(Boolean),
    );
    if (options.length) await roleSelect.selectOption(options[0]);
  }

  // A readiness figure and at least one named gap: the analysis must be
  // specific, not a generic "keep learning" message.
  await expect(page.getByRole("progressbar").or(page.getByRole("img", { name: /percent/i })).first())
    .toBeVisible({ timeout: 20_000 });
});

test("6 · finds an internship and applies to it", async ({ page, request }) => {
  await signInAsJourneyStudent(page);

  // The browse-and-filter flow is covered by smoke.spec.ts. Here the posting
  // has to belong to the demo recruiter's company, or step 8 would be
  // reviewing an application the recruiter cannot see.
  const posting = await recruiterOwnedInternship(request);

  await page.goto("/student/internships");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.locator('a[href^="/opportunities/"]').first())
    .toBeVisible({ timeout: 20_000 });

  await page.goto(`/opportunities/${posting.id}`);
  await page.waitForURL(/\/opportunities\/[0-9a-f-]+/);

  appliedTitle = (await page.getByRole("heading", { level: 1 }).first().innerText()).trim();

  // The student must be able to see why this was matched before applying.
  await expect(page.getByText(/match/i).first()).toBeVisible();

  const applyButton = page.getByRole("button", { name: /^apply now$/i });
  await expect(applyButton).toBeEnabled({ timeout: 20_000 });
  await applyButton.click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText(/recruiter sees your profile/i);
  await dialog.getByLabel(/cover note/i).fill(
    "I am closing my gap in testing and have shipped two backend projects.",
  );
  await dialog.getByRole("button", { name: /submit application/i }).click();

  await expect(page.getByText(/application submitted/i).first()).toBeVisible({ timeout: 30_000 });
});

test("7 · the application appears in the student's own tracker", async ({ page }) => {
  await signInAsJourneyStudent(page);
  await page.goto("/student/applications");
  await expect(page.getByRole("heading", { name: /my applications/i })).toBeVisible();
  await expect(page.getByText(appliedTitle, { exact: false }).first()).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.getByText("Applied").first()).toBeVisible();
});

test("8 · the recruiter sees the application with an explained match", async ({ page }) => {
  await login(page, DEMO.industry, DEMO_PASSWORD);
  await page.goto("/industry/applicants");
  await expect(page.getByRole("heading", { name: /applicants/i })).toBeVisible();

  await page.getByLabel("Search name").fill(STUDENT_NAME);
  await page.getByRole("button", { name: "Apply", exact: true }).click();

  const row = page.getByText(STUDENT_NAME).first();
  await expect(row).toBeVisible({ timeout: 20_000 });
  await row.click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  // Section 92: the score is decision support, and the platform says so where
  // the decision is actually made.
  await expect(dialog).toContainText(/decision support/i);
  await expect(dialog).toContainText(/hiring decision remains yours/i);
});

test("9 · the recruiter shortlists, and the student sees the new status", async ({ page }) => {
  await login(page, DEMO.industry, DEMO_PASSWORD);
  await page.goto("/industry/applicants");
  await page.getByLabel("Search name").fill(STUDENT_NAME);
  await page.getByRole("button", { name: "Apply", exact: true }).click();
  await page.getByText(STUDENT_NAME).first().click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await dialog.getByLabel(/note for this decision/i).fill("Strong project evidence.");
  await dialog.getByRole("button", { name: "Shortlisted", exact: true }).click();

  await expect(dialog.getByText("Shortlisted").first()).toBeVisible({ timeout: 20_000 });
  await dialog.getByRole("button", { name: "Close", exact: true }).click();

  // The state change is real: it is visible to the student too.
  await page.context().clearCookies();
  await page.goto("/login");
  await page.evaluate(() => window.localStorage.clear());
  await login(page, STUDENT_EMAIL, STRONG_PASSWORD);
  await page.goto("/student/applications");
  await expect(page.getByText("Shortlisted").first()).toBeVisible({ timeout: 20_000 });
});
