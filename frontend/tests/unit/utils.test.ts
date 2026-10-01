/**
 * Formatting and presentation helpers.
 *
 * These run on every page, so a regression here is visible everywhere. The
 * score bands in particular must match the backend's readiness language.
 */
import { describe, expect, it } from "vitest";
import {
  clamp,
  daysUntil,
  formatCurrency,
  formatDate,
  formatRange,
  initials,
  pluralise,
  relativeTime,
  scoreTone,
  titleCase,
} from "@/lib/utils";

describe("formatCurrency", () => {
  it("abbreviates using Indian conventions", () => {
    expect(formatCurrency(800)).toBe("₹800");
    expect(formatCurrency(25_000)).toBe("₹25k");
    expect(formatCurrency(1_200_000)).toBe("₹12L");
    expect(formatCurrency(1_250_000)).toBe("₹12.5L");
    expect(formatCurrency(25_000_000)).toBe("₹2.5Cr");
  });

  it("falls back to Intl for other currencies", () => {
    expect(formatCurrency(25_000, "USD")).toMatch(/25,000/);
  });

  it("returns a dash for missing values rather than NaN or ₹0", () => {
    expect(formatCurrency(null)).toBe("—");
    expect(formatCurrency(undefined)).toBe("—");
  });
});

describe("formatRange", () => {
  it("collapses an equal min and max to a single figure", () => {
    expect(formatRange(20000, 20000)).toBe(formatCurrency(20000));
  });

  it("shows the known bound when only one is set", () => {
    expect(formatRange(20_000, null)).toBe("₹20k");
    expect(formatRange(null, 40_000)).toBe("₹40k");
  });

  it("renders both bounds when they differ", () => {
    expect(formatRange(20_000, 40_000)).toBe("₹20k – ₹40k");
  });

  it("returns 'Not disclosed' when neither bound is set", () => {
    expect(formatRange(null, null)).toBe("Not disclosed");
  });
});

describe("formatDate", () => {
  it("formats an ISO date", () => {
    expect(formatDate("2026-03-14T00:00:00Z")).toMatch(/2026/);
  });

  it("degrades gracefully on empty or malformed input", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate("not-a-date")).toBe("—");
  });
});

describe("relativeTime", () => {
  it("describes the recent past", () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60_000).toISOString();
    expect(relativeTime(fiveMinutesAgo)).toMatch(/minute/);
  });

  it("describes the near future", () => {
    const inTwoDays = new Date(Date.now() + 2 * 86_400_000).toISOString();
    expect(relativeTime(inTwoDays)).toMatch(/day/);
  });
});

describe("daysUntil", () => {
  it("rounds up, so a deadline later today still reads as a day left", () => {
    expect(daysUntil(new Date(Date.now() + 3 * 86_400_000).toISOString())).toBe(3);
    expect(daysUntil(new Date(Date.now() + 3_600_000).toISOString())).toBe(1);
  });

  it("goes negative once a deadline has passed", () => {
    const yesterday = new Date(Date.now() - 86_400_000).toISOString();
    expect(daysUntil(yesterday)).toBeLessThan(0);
  });

  it("returns null when there is no date", () => {
    expect(daysUntil(null)).toBeNull();
  });
});

describe("initials", () => {
  it("takes the first letter of the first and last name", () => {
    expect(initials("Ananya Raghavan")).toBe("AR");
  });

  it("uses two letters of a single name, and ignores extra whitespace", () => {
    expect(initials("  ravi  ")).toBe("RA");
    expect(initials("Ananya   Devi   Raghavan")).toBe("AR");
  });

  it("falls back rather than rendering an empty avatar", () => {
    expect(initials("")).toBe("?");
    expect(initials(null)).toBe("?");
  });
});

describe("titleCase", () => {
  it("turns an enum value into prose", () => {
    expect(titleCase("UNDER_REVIEW")).toBe("Under Review");
    expect(titleCase("FULL_TIME")).toBe("Full Time");
  });
});

describe("pluralise", () => {
  it("uses the singular for exactly one", () => {
    expect(pluralise(1, "application")).toBe("1 application");
    expect(pluralise(0, "application")).toBe("0 applications");
    expect(pluralise(2, "match")).toBe("2 matchs"); // caller supplies irregulars
    expect(pluralise(2, "match", "matches")).toBe("2 matches");
  });
});

describe("clamp", () => {
  it("keeps a score inside 0-100 by default", () => {
    expect(clamp(140)).toBe(100);
    expect(clamp(-12)).toBe(0);
    expect(clamp(63)).toBe(63);
  });
});

describe("scoreTone", () => {
  it("bands scores consistently across the whole app", () => {
    expect(scoreTone(92)).toBe("success");
    expect(scoreTone(80)).toBe("success");
    expect(scoreTone(79)).toBe("brand");
    expect(scoreTone(60)).toBe("brand");
    expect(scoreTone(59)).toBe("warning");
    expect(scoreTone(35)).toBe("warning");
    expect(scoreTone(34)).toBe("danger");
    expect(scoreTone(0)).toBe("danger");
  });

  it("never leaves a valid score without a tone", () => {
    for (let score = 0; score <= 100; score += 1) {
      expect(["danger", "warning", "brand", "success"]).toContain(scoreTone(score));
    }
  });
});
