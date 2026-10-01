// @vitest-environment node
/**
 * Frontend/backend contract.
 *
 * The TypeScript union types and the Python enums are written independently,
 * so they can silently drift: a new application status added in the API would
 * render as an unlabelled chip, and a status transition the UI offers but the
 * API rejects would fail only when a recruiter clicks it.
 *
 * These tests read the backend enum module directly and compare. They are
 * skipped (not failed) when the backend source is not on disk, so the frontend
 * package stays independently installable.
 */
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import {
  APPLICATION_STATUS_LABELS,
  APPLICATION_STATUS_TONE,
  MATCH_FACTOR_LABELS,
  NEXT_STATUSES,
  PROFICIENCY_LABELS,
  PROFICIENCY_ORDER,
  ROLE_HOME,
  ROLE_LABELS,
} from "@/lib/constants";

// Vitest runs with the frontend package as its root.
const ENUMS_PATH = resolve(process.cwd(), "../backend/app/models/enums.py");
const CONFIG_PATH = resolve(process.cwd(), "../backend/app/core/config.py");
const TYPES_PATH = resolve(process.cwd(), "types/api.ts");

const backendAvailable = existsSync(ENUMS_PATH);
const describeContract = backendAvailable ? describe : describe.skip;

/** Members of a Python StrEnum, e.g. `APPLIED = "APPLIED"`. */
function pythonEnumMembers(source: string, className: string): string[] {
  const start = source.indexOf(`class ${className}(StrEnum):`);
  if (start === -1) throw new Error(`enum ${className} not found`);
  const rest = source.slice(start);
  const end = rest.indexOf("\nclass ", 1);
  const body = end === -1 ? rest : rest.slice(0, end);
  return [...body.matchAll(/^ {4}([A-Z][A-Z0-9_]*) = "([^"]+)"$/gm)].map((m) => m[2]);
}

/** Members of a TypeScript string-literal union type. */
function tsUnionMembers(source: string, typeName: string): string[] {
  const match = source.match(new RegExp(`export type ${typeName} =([\\s\\S]*?);`));
  if (!match) throw new Error(`type ${typeName} not found`);
  return [...match[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
}

describeContract("enum parity with the API", () => {
  const enums = backendAvailable ? readFileSync(ENUMS_PATH, "utf8") : "";
  const types = backendAvailable ? readFileSync(TYPES_PATH, "utf8") : "";

  it.each([
    ["RoleName", "RoleName"],
    ["ApplicationStatus", "ApplicationStatus"],
    ["ProficiencyLevel", "ProficiencyLevel"],
  ])("%s matches the TypeScript union", (pyName, tsName) => {
    expect(tsUnionMembers(types, tsName).sort()).toEqual(pythonEnumMembers(enums, pyName).sort());
  });

  it("every role has a label and a landing route", () => {
    for (const role of pythonEnumMembers(enums, "RoleName")) {
      expect(ROLE_LABELS[role as keyof typeof ROLE_LABELS]).toBeTruthy();
      expect(ROLE_HOME[role as keyof typeof ROLE_HOME]).toMatch(/^\//);
    }
  });

  it("every application status has a label and a tone", () => {
    for (const status of pythonEnumMembers(enums, "ApplicationStatus")) {
      expect(APPLICATION_STATUS_LABELS[status as keyof typeof APPLICATION_STATUS_LABELS]).toBeTruthy();
      expect(APPLICATION_STATUS_TONE[status as keyof typeof APPLICATION_STATUS_TONE]).toBeTruthy();
    }
  });

  it("every proficiency level is ordered and labelled", () => {
    const levels = pythonEnumMembers(enums, "ProficiencyLevel");
    expect([...PROFICIENCY_ORDER].sort()).toEqual([...levels].sort());
    for (const level of levels) {
      expect(PROFICIENCY_LABELS[level as keyof typeof PROFICIENCY_LABELS]).toBeTruthy();
    }
  });
});

describeContract("application status transitions", () => {
  const enums = backendAvailable ? readFileSync(ENUMS_PATH, "utf8") : "";

  /** Parse APPLICATION_TRANSITIONS into { FROM: [TO, ...] }. */
  function backendTransitions(): Record<string, string[]> {
    const start = enums.indexOf("APPLICATION_TRANSITIONS");
    const body = enums.slice(start, enums.indexOf("\n}\n", start));
    const out: Record<string, string[]> = {};
    const entry = /ApplicationStatus\.([A-Z_]+): (set\(\)|\{([\s\S]*?)\})/g;
    for (const match of body.matchAll(entry)) {
      const [, from, whole, inner] = match;
      out[from] = whole === "set()"
        ? []
        : [...inner.matchAll(/ApplicationStatus\.([A-Z_]+)/g)].map((m) => m[1]);
    }
    return out;
  }

  it("covers every status", () => {
    const transitions = backendTransitions();
    expect(Object.keys(transitions).sort()).toEqual(pythonEnumMembers(enums, "ApplicationStatus").sort());
    expect(Object.keys(NEXT_STATUSES).sort()).toEqual(Object.keys(transitions).sort());
  });

  it("never offers a transition the API would reject", () => {
    const transitions = backendTransitions();
    for (const [from, allowed] of Object.entries(NEXT_STATUSES)) {
      for (const to of allowed) {
        expect(
          transitions[from],
          `the recruiter UI offers ${from} → ${to}, which the API does not allow`,
        ).toContain(to);
      }
    }
  });

  it("treats the same statuses as terminal", () => {
    const transitions = backendTransitions();
    for (const [from, allowed] of Object.entries(transitions)) {
      if (allowed.length === 0) expect(NEXT_STATUSES[from as keyof typeof NEXT_STATUSES]).toEqual([]);
    }
  });

  it("leaves withdrawal to the student, not the recruiter", () => {
    for (const allowed of Object.values(NEXT_STATUSES)) {
      expect(allowed).not.toContain("WITHDRAWN");
    }
  });
});

describeContract("matching factors", () => {
  const config = backendAvailable ? readFileSync(CONFIG_PATH, "utf8") : "";

  it("labels every factor the scoring engine can return", () => {
    const factors = [...config.matchAll(/^ {4}MATCH_WEIGHT_([A-Z]+): float/gm)].map((m) =>
      m[1].toLowerCase(),
    );
    expect(factors.length).toBeGreaterThan(0);
    for (const factor of factors) {
      expect(MATCH_FACTOR_LABELS[factor], `no label for match factor "${factor}"`).toBeTruthy();
    }
  });

  it("uses default weights that sum to 1.0, as the API asserts at startup", () => {
    const weights = [...config.matchAll(/^ {4}MATCH_WEIGHT_[A-Z]+: float = ([\d.]+)/gm)].map((m) =>
      Number(m[1]),
    );
    expect(weights.reduce((a, b) => a + b, 0)).toBeCloseTo(1.0, 6);
  });
});
