/**
 * Deterministic fetch-level network router for tests. The routes and envelopes
 * mirror the live client (`lib/api/routes.ts`, `lib/api/schemas.ts`); nothing here
 * reaches the real API (L4). Unmatched calls throw loudly.
 */

import { REQUEST_ID_HEADER } from "../errors";
import { ROUTES } from "../routes";
import { formatSseEvent } from "../sse";
import {
  ABSTAINING_ANSWER,
  EMPTY_PAPER_RESULTS,
  ENGLISH_ANSWER,
  ERROR_BODY,
  FEEDBACK_VALIDATION_ERROR,
  IMAGE_ANSWER,
  PAPER_RESULTS,
  ROMAN_URDU_ANSWER,
  STREAM_EVENTS,
  URDU_ANSWER,
} from "./fixtures";

export type MockScenario =
  | "english"
  | "urdu"
  | "romanUrdu"
  | "stream"
  | "abstain"
  | "image"
  | "papers"
  | "emptyPapers"
  | "error"
  | "invalid"
  | "invalidStream"
  | "unknownStream"
  | "feedback422"
  | "feedback200"
  | "missingImage";

export type RecordedCall = { method: string; url: string; body: unknown };

/** Milliseconds between SSE frames — driven by fake timers in tests. */
export const STREAM_TICK_MS = 25;

const DEFAULT_SCENARIO: MockScenario = "english";
let scenario: MockScenario = DEFAULT_SCENARIO;
const calls: RecordedCall[] = [];

export function setMockScenario(next: MockScenario): void {
  scenario = next;
}

export function resetMockScenario(): void {
  scenario = DEFAULT_SCENARIO;
}

export function getMockCalls(): readonly RecordedCall[] {
  return calls;
}

export function lastMockCall(): RecordedCall | undefined {
  return calls[calls.length - 1];
}

export function clearMockCalls(): void {
  calls.length = 0;
}

/** Replace global fetch with the router; return a restore function. */
export function installMockFetch(): () => void {
  const original = globalThis.fetch;
  globalThis.fetch = mockFetch;
  return () => {
    globalThis.fetch = original;
  };
}

function answerForScenario(): unknown {
  switch (scenario) {
    case "urdu":
      return URDU_ANSWER;
    case "romanUrdu":
      return ROMAN_URDU_ANSWER;
    case "abstain":
      return ABSTAINING_ANSWER;
    case "image":
      return IMAGE_ANSWER;
    case "invalid":
      return { ...ENGLISH_ANSWER, language: "fr", invented_field: true };
    default:
      return ENGLISH_ANSWER;
  }
}

/** Real envelopes: ordered `token` frames and one authoritative `citations` frame. */
function eventsForScenario(): ReadonlyArray<{ event: string; payload: unknown }> {
  if (scenario === "invalidStream") {
    return [
      { event: "token", payload: { token: "Partial text only" } },
      { event: "citations", payload: { answer: { ...ENGLISH_ANSWER, language: "fr" } } },
    ];
  }
  if (scenario === "unknownStream") {
    return [
      { event: "token", payload: { token: "Partial text only" } },
      { event: "surprise", payload: { answer: ENGLISH_ANSWER } },
    ];
  }
  if (scenario === "stream") return STREAM_EVENTS;

  const answer =
    scenario === "urdu"
      ? URDU_ANSWER
      : scenario === "romanUrdu"
        ? ROMAN_URDU_ANSWER
        : scenario === "image"
          ? IMAGE_ANSWER
          : scenario === "english"
            ? ENGLISH_ANSWER
            : ABSTAINING_ANSWER;
  return [
    { event: "token", payload: { token: answer.text } },
    { event: "citations", payload: { answer } },
  ];
}

/** Emit one SSE frame per timer tick so incremental rendering is testable. */
function streamBody(): ReadableStream<Uint8Array> {
  const frames = eventsForScenario();
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      let index = 0;
      const push = (): void => {
        if (index >= frames.length) {
          controller.close();
          return;
        }
        const frame = frames[index];
        index += 1;
        controller.enqueue(encoder.encode(formatSseEvent(frame.event, frame.payload)));
        setTimeout(push, STREAM_TICK_MS);
      };
      setTimeout(push, 0);
    },
  });
}

async function mockFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  // jsdom's AbortSignal is not the Node Request's signal instance; the router
  // never aborts, so drop it before constructing a Request.
  const requestInit: RequestInit = { ...init };
  delete requestInit.signal;
  const request =
    input instanceof Request
      ? input
      : new Request(new URL(String(input), "http://localhost"), requestInit);
  const url = new URL(request.url);
  const path = url.pathname;

  let body: unknown = null;
  if (request.method !== "GET" && request.method !== "HEAD") {
    const text = await request.text();
    body = text === "" ? null : JSON.parse(text);
  }
  calls.push({ method: request.method, url: request.url, body });

  const jsonHeaders: Record<string, string> = {
    "content-type": "application/json",
    [REQUEST_ID_HEADER]: "req-trace-001",
  };
  const json = (data: unknown, status = 200, traceId = "req-trace-001"): Response =>
    new Response(JSON.stringify(data), {
      status,
      headers: { ...jsonHeaders, [REQUEST_ID_HEADER]: traceId },
    });

  if (path === ROUTES.query && request.method === "POST") {
    if (scenario === "error") return json(ERROR_BODY, 503, "req-error-503");
    return json(answerForScenario());
  }
  if (path === ROUTES.feedback && request.method === "POST") {
    if (scenario === "feedback422") return json(FEEDBACK_VALIDATION_ERROR, 422, "req-feedback-422");
    if (scenario === "feedback200") return json(body, 200, "req-feedback-200");
    return json(body, 202, "req-feedback-202");
  }
  if (path === ROUTES.stream && request.method === "POST") {
    if (scenario === "error") return json(ERROR_BODY, 503, "req-error-stream-503");
    return new Response(streamBody(), {
      status: 200,
      headers: {
        "content-type": "text/event-stream",
        [REQUEST_ID_HEADER]: "req-trace-stream-001",
      },
    });
  }
  if (path === ROUTES.papers && request.method === "GET") {
    if (scenario === "emptyPapers") return json(EMPTY_PAPER_RESULTS);
    if (scenario === "error") return json(ERROR_BODY, 503);
    return json({ results: PAPER_RESULTS });
  }
  if (path.startsWith(ROUTES.imagesPrefix) && request.method === "GET") {
    if (scenario === "missingImage") return json(ERROR_BODY, 404, "req-image-404");
    const pixel = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
      "base64",
    );
    return new Response(pixel, { status: 200, headers: { "content-type": "image/png" } });
  }
  if (scenario === "error") return json(ERROR_BODY, 503, "req-error-503");

  throw new Error(`No mock handler for ${request.method} ${path} (scenario: ${scenario})`);
}
