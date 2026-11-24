import axe from "axe-core";
import { expect } from "vitest";

/** Pin zero critical axe violations for a rendered page (L1). */
export async function expectNoCriticalA11yViolations(container: HTMLElement): Promise<void> {
  const results = await axe.run(container, { resultTypes: ["violations"] });
  const critical = results.violations
    .filter((violation) => violation.impact === "critical")
    .map((violation) => `${violation.id}: ${violation.help}`);
  expect(critical).toEqual([]);
}
