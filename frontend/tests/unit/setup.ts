import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Contract tests declare `@vitest-environment node`; the DOM shims below do
// not apply to them and `window` does not exist there.
const hasDom = typeof window !== "undefined";

// jsdom implements neither of these; Recharts and the dialog/tooltip
// components call them during render.
if (hasDom && !window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;
}

if (hasDom && !window.ResizeObserver) {
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

if (hasDom && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}

// Node's own `localStorage` global is disabled without --localstorage-file and
// shadows jsdom's, so the token store would have nowhere to write.
if (hasDom && !globalThis.localStorage) {
  const store = new Map<string, string>();
  const shim: Storage = {
    get length() {
      return store.size;
    },
    key: (index) => [...store.keys()][index] ?? null,
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => void store.set(key, String(value)),
    removeItem: (key) => void store.delete(key),
    clear: () => store.clear(),
  };
  Object.defineProperty(globalThis, "localStorage", { value: shim, configurable: true });
  Object.defineProperty(window, "localStorage", { value: shim, configurable: true });
}

afterEach(() => {
  if (hasDom) {
    cleanup();
    window.localStorage.clear();
  }
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
