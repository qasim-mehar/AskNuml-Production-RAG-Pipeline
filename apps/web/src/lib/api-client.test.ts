import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchJson } from "./api-client";

describe("fetchJson", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("parses a successful JSON response", async () => {
    const response = new Response(JSON.stringify({ status: "ok" }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    await expect(fetchJson<{ status: string }>("/health")).resolves.toEqual({ status: "ok" });
  });

  it("rejects a non-ok response", async () => {
    const response = new Response("down", { status: 503 });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    await expect(fetchJson("/health")).rejects.toThrow("503");
  });
});
