import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { lastMockCall, setMockScenario } from "@/lib/api/mocks/handlers";
import { expectNoCriticalA11yViolations } from "@/test/a11y";

import { PapersPage } from "./PapersPage";

function fillFilters(): void {
  fireEvent.change(screen.getByLabelText("Course code"), { target: { value: "CS" } });
  fireEvent.change(screen.getByLabelText("Year"), { target: { value: "2024" } });
  fireEvent.change(screen.getByLabelText("Term"), { target: { value: "fall" } });
  fireEvent.change(screen.getByLabelText("Exam type"), { target: { value: "final" } });
  fireEvent.change(screen.getByLabelText("Department"), {
    target: { value: "کمپیوٹر سائنس" },
  });
}

function search(): void {
  fireEvent.click(screen.getByRole("button", { name: "Find past papers" }));
}

describe("PapersPage", () => {
  it("turns every filter into the expected mock query, including an Urdu department", async () => {
    setMockScenario("papers");
    render(<PapersPage />);
    fillFilters();
    search();

    await screen.findByRole("list", { name: "Past-paper results" });
    const url = new URL(lastMockCall()?.url ?? "http://localhost/");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      course_code: "CS",
      year: "2024",
      term: "fall",
      exam_type: "final",
      department: "کمپیوٹر سائنس",
    });
  });

  it("renders an explicit empty state instead of a silent blank", async () => {
    setMockScenario("emptyPapers");
    const { container } = render(<PapersPage />);
    fillFilters();
    search();

    expect(
      await screen.findByText("No past papers match these filters."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Past-paper results" })).not.toBeInTheDocument();
    await expectNoCriticalA11yViolations(container);
  });

  it("renders results with provenance and passes axe with zero critical violations", async () => {
    setMockScenario("papers");
    const { container } = render(<PapersPage />);
    search();

    expect(await screen.findByRole("list", { name: "Past-paper results" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Source PDF" })[0]).toHaveAttribute(
      "href",
      "https://uni.example/archive/cs-2024-final.pdf",
    );
    expect(screen.getByRole("img")).toHaveAttribute("alt", "Past paper page 2");
    await expectNoCriticalA11yViolations(container);

    const interactive = Array.from(
      container.querySelectorAll<HTMLElement>("button, a[href], input, select, textarea"),
    );
    for (const element of interactive) {
      element.focus();
      expect(document.activeElement).toBe(element);
    }
  });

  it("shows a typed error with the trace request id", async () => {
    setMockScenario("error");
    render(<PapersPage />);
    search();
    await waitFor(async () => {
      expect(await screen.findByRole("alert")).toHaveTextContent("req-trace-001");
    });
  });
});
