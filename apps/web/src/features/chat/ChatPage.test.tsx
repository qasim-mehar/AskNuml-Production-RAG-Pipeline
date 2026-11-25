import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  ABSTAINING_ANSWER,
  CITATION,
  ENGLISH_ANSWER,
  IMAGE_REF,
  URDU_ANSWER,
} from "@/lib/api/mocks/fixtures";
import contract from "@/lib/api/mocks/openapi-emitted.json";
import {
  lastMockCall,
  setMockScenario,
  STREAM_TICK_MS,
} from "@/lib/api/mocks/handlers";
import { expectNoCriticalA11yViolations } from "@/test/a11y";

import { ChatPage } from "./ChatPage";

function ask(question: string): void {
  fireEvent.change(screen.getByLabelText("Your question"), { target: { value: question } });
  fireEvent.click(screen.getByRole("button", { name: "Ask" }));
}

/** Let the final commit land after the last timer-driven stream frame. */
async function drainStream(): Promise<void> {
  await act(async () => {
    await vi.runAllTimersAsync();
  });
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

function expectInteractiveElementsFocusable(container: HTMLElement): void {
  const interactive = Array.from(
    container.querySelectorAll<HTMLElement>("button, a[href], input, select, textarea"),
  );
  expect(interactive.length).toBeGreaterThan(0);
  for (const element of interactive) {
    element.focus();
    expect(document.activeElement).toBe(element);
  }
}

describe("ChatPage", () => {
  it("renders tokens incrementally, then exact citation chips and the inline page image", async () => {
    vi.useFakeTimers();
    setMockScenario("stream");
    const { container } = render(<ChatPage />);
    ask("What is the fee?");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(STREAM_TICK_MS);
    });
    expect(screen.getByRole("status")).toHaveTextContent("Answering");
    const streaming = screen.getByRole("region", { name: "Streaming answer" });
    expect(streaming.textContent?.length).toBeGreaterThan(0);
    expect(streaming.textContent).not.toBe(ENGLISH_ANSWER.text);

    await drainStream();
    vi.useRealTimers(); // axe needs real timers to finish its async rule passes
    const answerSpans = within(screen.getByRole("list", { name: "Conversation" })).getAllByText(
      ENGLISH_ANSWER.text,
    );
    expect(
      answerSpans.some(
        (element) => element.closest("article")?.getAttribute("data-role") === "assistant",
      ),
    ).toBe(true);

    const chip = within(screen.getByRole("list", { name: "Citations" }))
      .getByText(CITATION.snippet)
      .closest("li");
    expect(chip).toHaveAttribute("data-chunk-id", CITATION.chunk_id);
    expect(chip).toHaveAttribute("data-doc-id", CITATION.doc_id);
    expect(screen.getByText(CITATION.source_url)).toBeInTheDocument();
    expect(screen.getByText("Updated 20 Nov 2026")).toBeInTheDocument();
    expect(screen.getByText(`Page ${CITATION.page ?? ""}`)).toBeInTheDocument();
    expect(screen.getByRole("img")).toHaveAttribute("alt", IMAGE_REF.caption ?? "");

    await expectNoCriticalA11yViolations(container);
  }, 20_000);

  it("renders abstention guidance with no fabricated citation chips", async () => {
    setMockScenario("abstain");
    render(<ChatPage />);
    ask("When is the fee due?");

    expect(
      await screen.findByText(/not enough evidence/i, { exact: false }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Citations" })).not.toBeInTheDocument();
    expect(ABSTAINING_ANSWER.citations).toEqual([]);
  });

  it("renders an Urdu answer right-to-left", async () => {
    setMockScenario("urdu");
    render(<ChatPage />);
    ask("فیس کتنی ہے؟");

    const bubble = await screen.findByText(URDU_ANSWER.text);
    expect(bubble).toBeInTheDocument();
    expect(bubble.closest("article")).toHaveAttribute("dir", "rtl");
  });

  it("posts feedback with the committed answer id and sentiment", async () => {
    setMockScenario("english");
    render(<ChatPage />);
    ask("What is the fee?");
    await screen.findByRole("region", {
      name: `Feedback for answer ${ENGLISH_ANSWER.answer_id}`,
    });

    fireEvent.click(screen.getByRole("button", { name: "Helpful" }));
    fireEvent.click(screen.getByRole("button", { name: "Send feedback" }));

    await waitFor(() =>
      expect(new URL(lastMockCall()?.url ?? "http://localhost/").pathname).toBe(
        contract.conventions.feedback,
      ),
    );
    expect(lastMockCall()?.body).toMatchObject({
      answer_id: ENGLISH_ANSWER.answer_id,
      sentiment: "positive",
    });
  });

  it("keeps feedback retryable and shows the trace id when the API rejects it", async () => {
    setMockScenario("english");
    render(<ChatPage />);
    ask("What is the fee?");
    await screen.findByRole("region", {
      name: `Feedback for answer ${ENGLISH_ANSWER.answer_id}`,
    });

    setMockScenario("feedback422");
    fireEvent.click(screen.getByRole("button", { name: "Helpful" }));
    fireEvent.click(screen.getByRole("button", { name: "Send feedback" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("req-feedback-422");
    expect(screen.queryByText("Thanks for your feedback.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send feedback" })).toBeInTheDocument();
  });

  it("surfaces a typed schema error with no partial render for an invalid stream", async () => {
    vi.useFakeTimers();
    setMockScenario("invalidStream");
    render(<ChatPage />);
    ask("What is the fee?");

    await drainStream();
    expect(screen.getByRole("alert")).toHaveTextContent("Invalid citations event");
    expect(screen.queryByText("Partial text only")).not.toBeInTheDocument();
  });

  it("shows the trace request id on a typed HTTP error", async () => {
    setMockScenario("error");
    render(<ChatPage />);
    ask("What is the fee?");
    expect(await screen.findByRole("alert")).toHaveTextContent("req-error-stream-503");
  });

  it("exposes every interactive element to keyboard focus", () => {
    const { container } = render(<ChatPage />);
    expectInteractiveElementsFocusable(container);
  });
});
