/**
 * Theme selection, persistence and the system-preference default.
 *
 * The behaviours worth pinning are the ones a user would notice and could not
 * easily diagnose: a choice that does not survive a reload, a "system" setting
 * that stops following the system, and an explicit choice that gets
 * overwritten by the OS.
 */
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ThemeToggle } from "@/components/ui/theme-toggle";
import { THEME_STORAGE_KEY, ThemeProvider, useTheme } from "@/lib/theme";

/** A controllable prefers-color-scheme, with listener support. */
function mockSystemPreference(prefersDark: boolean) {
  const listeners = new Set<(event: MediaQueryListEvent) => void>();
  const query = {
    matches: prefersDark,
    media: "(prefers-color-scheme: dark)",
    onchange: null,
    addEventListener: (_: string, fn: (e: MediaQueryListEvent) => void) => {
      listeners.add(fn);
    },
    removeEventListener: (_: string, fn: (e: MediaQueryListEvent) => void) => {
      listeners.delete(fn);
    },
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  } as unknown as MediaQueryList;

  vi.stubGlobal("matchMedia", vi.fn().mockReturnValue(query));

  return {
    /** Simulate the OS flipping to the other scheme. */
    change(nowDark: boolean) {
      (query as { matches: boolean }).matches = nowDark;
      listeners.forEach((fn) => fn({ matches: nowDark } as MediaQueryListEvent));
    },
  };
}

function Probe() {
  const { theme, resolvedTheme, isReady } = useTheme();
  return (
    <div>
      <span data-testid="choice">{theme}</span>
      <span data-testid="resolved">{resolvedTheme}</span>
      <span data-testid="ready">{String(isReady)}</span>
    </div>
  );
}

const isDark = () => document.documentElement.classList.contains("dark");

beforeEach(() => {
  document.documentElement.classList.remove("dark");
  document.documentElement.removeAttribute("style");
  delete document.documentElement.dataset.theme;
  window.localStorage.clear();
});

describe("initial theme", () => {
  it("follows the system preference when nothing is stored", async () => {
    mockSystemPreference(true);
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("ready")).toHaveTextContent("true"));
    expect(screen.getByTestId("choice")).toHaveTextContent("system");
    expect(screen.getByTestId("resolved")).toHaveTextContent("dark");
    expect(isDark()).toBe(true);
  });

  it("uses light when the system prefers light and nothing is stored", async () => {
    mockSystemPreference(false);
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("resolved")).toHaveTextContent("light"));
    expect(isDark()).toBe(false);
  });

  it("prefers a stored choice over the system preference", async () => {
    mockSystemPreference(true);
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");

    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("ready")).toHaveTextContent("true"));
    expect(screen.getByTestId("choice")).toHaveTextContent("light");
    expect(isDark()).toBe(false);
  });

  it("ignores a corrupted stored value rather than failing to render", async () => {
    mockSystemPreference(false);
    window.localStorage.setItem(THEME_STORAGE_KEY, "aubergine");

    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("choice")).toHaveTextContent("system"));
    expect(isDark()).toBe(false);
  });

  it("sets color-scheme so native controls and scrollbars follow", async () => {
    mockSystemPreference(true);
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );
    await waitFor(() => expect(document.documentElement.style.colorScheme).toBe("dark"));
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});

describe("switching", () => {
  it("toggles light to dark and persists the choice", async () => {
    mockSystemPreference(false);
    render(
      <ThemeProvider>
        <Probe />
        <ThemeToggle />
      </ThemeProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("ready")).toHaveTextContent("true"));

    await userEvent.click(screen.getByRole("button", { name: /switch to dark theme/i }));

    expect(isDark()).toBe(true);
    expect(screen.getByTestId("resolved")).toHaveTextContent("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("toggles back, and the button always names what the click will do", async () => {
    mockSystemPreference(false);
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    );

    const toDark = await screen.findByRole("button", { name: /switch to dark theme/i });
    await userEvent.click(toDark);

    const toLight = await screen.findByRole("button", { name: /switch to light theme/i });
    await userEvent.click(toLight);

    expect(isDark()).toBe(false);
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
  });

  it("survives storage being unavailable", async () => {
    mockSystemPreference(false);
    const setItem = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new Error("QuotaExceededError");
      });

    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    );

    await userEvent.click(await screen.findByRole("button", { name: /switch to dark/i }));
    // The choice still applies for this page view even though it cannot persist.
    expect(isDark()).toBe(true);
    setItem.mockRestore();
  });
});

describe("the three-way control", () => {
  it("exposes light, dark and system as radios", async () => {
    mockSystemPreference(false);
    render(
      <ThemeProvider>
        <ThemeToggle menu />
      </ThemeProvider>,
    );

    const group = screen.getByRole("radiogroup", { name: /colour theme/i });
    expect(group).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Light" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Dark" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "System" })).toBeInTheDocument();
  });

  it("marks the active choice and stores an explicit selection", async () => {
    mockSystemPreference(false);
    render(
      <ThemeProvider>
        <ThemeToggle menu />
      </ThemeProvider>,
    );

    await waitFor(() =>
      expect(screen.getByRole("radio", { name: "System" })).toHaveAttribute("aria-checked", "true"),
    );

    await userEvent.click(screen.getByRole("radio", { name: "Dark" }));
    expect(screen.getByRole("radio", { name: "Dark" })).toHaveAttribute("aria-checked", "true");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(isDark()).toBe(true);
  });
});

describe("following the system", () => {
  it("keeps following the OS while the choice is 'system'", async () => {
    const system = mockSystemPreference(false);
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("resolved")).toHaveTextContent("light"));

    act(() => system.change(true));

    await waitFor(() => expect(screen.getByTestId("resolved")).toHaveTextContent("dark"));
    expect(isDark()).toBe(true);
  });

  it("stops following once the user chooses explicitly", async () => {
    const system = mockSystemPreference(false);
    render(
      <ThemeProvider>
        <Probe />
        <ThemeToggle />
      </ThemeProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("ready")).toHaveTextContent("true"));

    await userEvent.click(screen.getByRole("button", { name: /switch to dark theme/i }));
    expect(screen.getByTestId("choice")).toHaveTextContent("dark");

    // The OS goes light; the user's explicit choice must win.
    act(() => system.change(false));

    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.getByTestId("resolved")).toHaveTextContent("dark");
    expect(isDark()).toBe(true);
  });
});

describe("useTheme outside a provider", () => {
  it("fails loudly rather than silently rendering the wrong theme", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Probe />)).toThrow(/useTheme must be used inside/);
    spy.mockRestore();
  });
});
