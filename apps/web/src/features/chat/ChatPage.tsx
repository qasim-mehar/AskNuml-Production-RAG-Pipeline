"use client";

import { type FormEvent, useState } from "react";

import { CitationChip } from "@/components/CitationChip";
import { FeedbackButtons } from "@/components/FeedbackButtons";
import { MessageBubble } from "@/components/MessageBubble";
import { PageImage } from "@/components/PageImage";
import { type Language } from "@/lib/api/schemas";
import { detectLanguage } from "@/lib/format/language";

import { useChat } from "./useChat";

const LANGUAGE_OPTIONS = [
  { value: "en", label: "English" },
  { value: "ur", label: "Urdu" },
  { value: "roman_urdu", label: "Roman Urdu" },
  { value: "auto", label: "Detect language" },
] as const;

/** Cited streaming chat composition. Every fact on screen comes from the API. */
export function ChatPage() {
  const { turns, draft, status, error, send, submitFeedback } = useChat();
  const [text, setText] = useState("");
  const [language, setLanguage] = useState<Language | "auto">("auto");

  const submit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const trimmed = text.trim();
    if (trimmed === "") return;
    const resolved: Language = language === "auto" ? detectLanguage(trimmed) : language;
    void send(trimmed, resolved);
    setText("");
  };

  const lastAnswer = [...turns].reverse().find((turn) => turn.answer !== undefined);
  const feedbackAnswerId = lastAnswer?.answer?.answer_id;

  return (
    <main>
      <h1>Ask uni-rag</h1>
      <p>Answers are cited. If evidence is weak, the assistant says so and suggests a next step.</p>

      <form onSubmit={submit}>
        <label htmlFor="chat-question">Your question</label>
        <textarea
          id="chat-question"
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <label htmlFor="chat-language">Language</label>
        <select
          id="chat-language"
          value={language}
          onChange={(event) => setLanguage(event.target.value as Language | "auto")}
        >
          {LANGUAGE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <button type="submit" disabled={status === "streaming"}>
          Ask
        </button>
      </form>

      {status === "streaming" ? <p role="status">Answering…</p> : null}
      {error ? (
        <div role="alert" className="error">
          {error.message}
          {error.requestId ? <> (request id: {error.requestId})</> : null}
        </div>
      ) : null}

      <ol aria-label="Conversation">
        {turns.map((turn) => (
          <li key={turn.id}>
            <MessageBubble text={turn.text} language={turn.language} role={turn.role} />
            {turn.answer && !turn.answer.abstained ? (
              <>
                {turn.answer.citations.length > 0 ? (
                  <ul aria-label="Citations">
                    {turn.answer.citations.map((citation) => (
                      <CitationChip key={citation.chunk_id} citation={citation} />
                    ))}
                  </ul>
                ) : null}
                {turn.answer.images.map((image) => (
                  <PageImage key={image.ref_id} image={image} />
                ))}
              </>
            ) : null}
          </li>
        ))}
      </ol>

      {draft ? (
        <section aria-label="Streaming answer">
          <MessageBubble text={draft.text} language={draft.language} role="assistant" />
        </section>
      ) : null}

      {feedbackAnswerId && status !== "streaming" ? (
        <FeedbackButtons
          answerId={feedbackAnswerId}
          onSubmit={(sentiment, reason) => submitFeedback(feedbackAnswerId, sentiment, reason)}
        />
      ) : null}
    </main>
  );
}
