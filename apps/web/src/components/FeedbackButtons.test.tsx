import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FeedbackButtons } from "./FeedbackButtons";

describe("FeedbackButtons", () => {
  it("submits the selected sentiment with an optional reason", async () => {
    const onSubmit = vi.fn().mockResolvedValue(true);
    render(<FeedbackButtons answerId="answer-1" onSubmit={onSubmit} />);

    fireEvent.click(screen.getByRole("button", { name: "Helpful" }));
    expect(screen.getByRole("button", { name: "Helpful" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.change(screen.getByLabelText("Reason (optional)"), {
      target: { value: "Clear citation" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send feedback" }));

    expect(onSubmit).toHaveBeenCalledWith("positive", "Clear citation");
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Thanks for your feedback."),
    );
  });

  it("does not claim success when the submission is rejected", async () => {
    const onSubmit = vi.fn().mockResolvedValue(false);
    render(<FeedbackButtons answerId="answer-3" onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "Helpful" }));
    fireEvent.click(screen.getByRole("button", { name: "Send feedback" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send feedback" })).toBeInTheDocument();
  });

  it("omits the reason when the student leaves it blank", () => {
    const onSubmit = vi.fn();
    render(<FeedbackButtons answerId="answer-2" onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "Not helpful" }));
    fireEvent.click(screen.getByRole("button", { name: "Send feedback" }));
    expect(onSubmit).toHaveBeenCalledWith("negative", undefined);
  });
});
