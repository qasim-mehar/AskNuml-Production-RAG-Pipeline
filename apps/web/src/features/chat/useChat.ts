"use client";

import { useCallback, useRef, useState } from "react";

import { feedback as sendFeedbackRequest, stream } from "@/lib/api/client";
import { ApiError, logClientError } from "@/lib/api/errors";
import {
  type Answer,
  type Language,
  type Sentiment,
  QuerySchema,
} from "@/lib/api/schemas";

export type ChatTurn = {
  id: string;
  role: "user" | "assistant";
  text: string;
  language: Language;
  answer?: Answer;
};

export type DraftAnswer = {
  text: string;
  language: Language;
};

export type ChatStatus = "idle" | "streaming" | "error";

/** Composes the live streamed API client into UI state. No fetching in components. */
export function useChat() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState<DraftAnswer | null>(null);
  const [status, setStatus] = useState<ChatStatus>("idle");
  const [error, setError] = useState<ApiError | null>(null);
  const counter = useRef(0);

  const send = useCallback(async (text: string, language: Language) => {
    counter.current += 1;
    const id = counter.current;
    const query = QuerySchema.parse({
      query_id: `q-${id}`,
      text,
      language,
      top_k: 10,
      filters: {},
    });

    setTurns((previous) => [
      ...previous,
      { id: `user-${id}`, role: "user", text, language },
    ]);
    setDraft({ text: "", language });
    setStatus("streaming");
    setError(null);

    try {
      // The real stream sends tokens only; citations/images arrive in the final
      // `citations` event and are rendered from that validated Answer (L5).
      const answer = await stream(query, {
        onToken: (token) =>
          setDraft((previous) => (previous ? { ...previous, text: previous.text + token } : previous)),
      });
      setTurns((previous) => [
        ...previous,
        {
          id: `assistant-${id}`,
          role: "assistant",
          text: answer.text,
          language: answer.language,
          answer,
        },
      ]);
      setDraft(null);
      setStatus("idle");
    } catch (cause) {
      const apiError =
        cause instanceof ApiError
          ? cause
          : new ApiError(String(cause), "schema", 0, null, "unexpected_client_error");
      logClientError(apiError, "chat.stream");
      // Clear draft on failure: an invalid payload must never partially render (L11).
      setDraft(null);
      setError(apiError);
      setStatus("error");
    }
  }, []);

  /** Returns true only when the API accepted the feedback; failures surface as errors. */
  const submitFeedback = useCallback(
    async (answerId: string, sentiment: Sentiment, reason?: string): Promise<boolean> => {
      try {
        await sendFeedbackRequest({ answer_id: answerId, sentiment, reason });
        return true;
      } catch (cause) {
        const apiError =
          cause instanceof ApiError
            ? cause
            : new ApiError(String(cause), "schema", 0, null, "unexpected_client_error");
        logClientError(apiError, "chat.feedback");
        setError(apiError);
        setStatus("error");
        return false;
      }
    },
    [],
  );

  return { turns, draft, status, error, send, submitFeedback };
}
