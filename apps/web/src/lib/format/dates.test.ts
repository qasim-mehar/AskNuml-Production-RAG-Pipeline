import { describe, expect, it } from "vitest";

import { formatLastUpdated } from "./dates";

describe("formatLastUpdated", () => {
  it("formats a timestamp deterministically in UTC", () => {
    expect(formatLastUpdated("2026-11-20T09:30:00Z")).toBe("20 Nov 2026");
    expect(formatLastUpdated("2026-01-02T23:59:59Z")).toBe("02 Jan 2026");
  });

  it("never invents a date: an unparseable payload value is shown verbatim", () => {
    expect(formatLastUpdated("last Tuesday")).toBe("last Tuesday");
  });
});
