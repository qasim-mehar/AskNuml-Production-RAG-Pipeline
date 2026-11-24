"use client";

import { useState } from "react";

import type { Sentiment } from "@/lib/api/schemas";

type FeedbackButtonsProps = {
  answerId: string;
  /** Resolves true only when the submission was accepted; false keeps the form retryable. */
  onSubmit: (sentiment: Sentiment, reason?: string) => boolean | Promise<boolean>;
  disabled?: boolean;
};

/** Presentational feedback capture: sentiment plus optional reason. */
export function FeedbackButtons({ answerId, onSubmit, disabled = false }: FeedbackButtonsProps) {
  const [selected, setSelected] = useState<Sentiment | null>(null);
  const [reason, setReason] = useState("");
  const [sent, setSent] = useState(false);

  return (
    <section className="feedback" aria-label={`Feedback for answer ${answerId}`}>
      {sent ? (
        <p role="status">Thanks for your feedback.</p>
      ) : (
        <>
          <button
            type="button"
            aria-pressed={selected === "positive"}
            disabled={disabled}
            onClick={() => setSelected("positive")}
          >
            Helpful
          </button>
          <button
            type="button"
            aria-pressed={selected === "negative"}
            disabled={disabled}
            onClick={() => setSelected("negative")}
          >
            Not helpful
          </button>
          {selected ? (
            <>
              <label htmlFor={`feedback-reason-${answerId}`}>Reason (optional)</label>
              <textarea
                id={`feedback-reason-${answerId}`}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
              <button
                type="button"
                disabled={disabled}
                onClick={() => {
                  const chosen = selected;
                  if (chosen === null) return;
                  void (async () => {
                    const trimmed = reason.trim();
                    const accepted = await onSubmit(
                      chosen,
                      trimmed === "" ? undefined : trimmed,
                    );
                    if (accepted) setSent(true);
                  })();
                }}
              >
                Send feedback
              </button>
            </>
          ) : null}
        </>
      )}
    </section>
  );
}
