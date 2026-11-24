import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, vi } from "vitest";

import {
  clearMockCalls,
  installMockFetch,
  resetMockScenario,
} from "@/lib/api/mocks/handlers";

let restoreFetch: () => void = () => undefined;

beforeAll(() => {
  // axe-core probes colour contrast via canvas; jsdom has no canvas backend.
  HTMLCanvasElement.prototype.getContext = (() =>
    null) as unknown as typeof HTMLCanvasElement.prototype.getContext;
  restoreFetch = installMockFetch();
  if (typeof window.matchMedia !== "function") {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (query: string): MediaQueryList =>
        ({
          matches: false,
          media: query,
          onchange: null,
          addListener: () => undefined,
          removeListener: () => undefined,
          addEventListener: () => undefined,
          removeEventListener: () => undefined,
          dispatchEvent: () => false,
        }) as unknown as MediaQueryList,
    });
  }
});

afterEach(() => {
  cleanup();
  clearMockCalls();
  resetMockScenario();
  vi.useRealTimers();
});

afterAll(() => {
  restoreFetch();
});
