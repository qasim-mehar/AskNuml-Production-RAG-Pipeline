import { describe, expect, it } from "vitest";

import {
  detectLanguage,
  directionFor,
  langTagFor,
  splitDirectionRuns,
} from "./language";

describe("language and direction", () => {
  it("renders Urdu right-to-left and English/Roman Urdu left-to-right", () => {
    expect(directionFor("ur")).toBe("rtl");
    expect(directionFor("en")).toBe("ltr");
    expect(directionFor("roman_urdu")).toBe("ltr");
    expect(langTagFor("roman_urdu")).toBe("ur-Latn");
  });

  it("detects Urdu, Roman Urdu and English from text", () => {
    expect(detectLanguage("فیس کتنی ہے؟")).toBe("ur");
    expect(detectLanguage("CS ki fee kya hai?")).toBe("roman_urdu");
    expect(detectLanguage("What is the tuition fee?")).toBe("en");
  });

  it("keeps each run's direction in a mixed English/Urdu message", () => {
    const runs = splitDirectionRuns("Fee is ready — فیس تیار ہے۔");
    expect(runs.map((run) => run.direction)).toEqual(["ltr", "rtl"]);
    expect(runs[0]?.text).toBe("Fee is ready — ");
    expect(runs[1]?.text).toBe("فیس تیار ہے۔");
  });

  it("returns one left-to-right run for plain Latin text", () => {
    expect(splitDirectionRuns("Hello")).toEqual([{ text: "Hello", direction: "ltr" }]);
  });
});
