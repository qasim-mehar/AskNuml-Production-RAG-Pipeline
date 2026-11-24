/**
 * MSW-equivalent deterministic network handlers. Root `pnpm-workspace.yaml`
 * gates dependency build scripts and `msw` cannot be approved without editing
 * Lane 0-owned config, so this router stubs global fetch instead (L4: no real
 * network in tests). Same handler/scenario semantics, zero ambient state.
 */

import { REQUEST_ID_HEADER } from "../errors";
import { formatSseEvent } from "../sse";
import {
  ABSTAINING_ANSWER,
  EMPTY_PAPER_RESULTS,
  ENGLISH_ANSWER,
  ERROR_BODY,
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
  | "invalidStream";

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

/** Scenario-aware SSE frames; the final answer always commits the payload. */
function eventsForScenario(): ReadonlyArray<{ event: string; payload: unknown }> {
  if (scenario === "invalidStream") {
    return [
      { event: "token", payload: { type: "token", text: "Partial text only" } },
      {
        event: "answer",
        payload: { type: "answer", answer: { ...ENGLISH_ANSWER, language: "fr" } },
      },
    ];
  }
  if (scenario === "abstain") {
    return [
      { event: "token", payload: { type: "token", text: ABSTAINING_ANSWER.text } },
      { event: "answer", payload: { type: "answer", answer: ABSTAINING_ANSWER } },
    ];
  }
  if (scenario === "urdu" || scenario === "romanUrdu" || scenario === "image") {
    const answer =
      scenario === "urdu" ? URDU_ANSWER : scenario === "image" ? IMAGE_ANSWER : ROMAN_URDU_ANSWER;
    const frames: Array<{ event: string; payload: unknown }> = [
      { event: "token", payload: { type: "token", text: answer.text } },
    ];
    for (const citation of answer.citations) {
      frames.push({ event: "citation", payload: { type: "citation", citation } });
    }
    for (const image of answer.images) {
      frames.push({ event: "image", payload: { type: "image", image } });
    }
    frames.push({ event: "answer", payload: { type: "answer", answer } });
    return frames;
  }
  return STREAM_EVENTS;
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
  // jsdom's AbortSignal is not the Node Request's signal instance; the mocks
  // never abort, so drop it before constructing a Request.
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
  const json = (data: unknown, status = 200): Response =>
    new Response(JSON.stringify(data), { status, headers: jsonHeaders });

  if (path === "/api/query" && request.method === "POST") {
    if (scenario === "error") {
      return new Response(JSON.stringify(ERROR_BODY), {
        status: 503,
        headers: { ...jsonHeaders, [REQUEST_ID_HEADER]: "req-error-503" },
      });
    }
    return json(answerForScenario());
  }
  if (path === "/api/feedback" && request.method === "POST") {
    return new Response(null, { status: 204, headers: jsonHeaders });
  }
  if (path === "/api/query/stream" && request.method === "POST") {
    if (scenario === "error") {
      return new Response(JSON.stringify(ERROR_BODY), {
        status: 503,
        headers: { ...jsonHeaders, [REQUEST_ID_HEADER]: "req-error-stream-503" },
      });
    }
    return new Response(streamBody(), {
      status: 200,
      headers: {
        "content-type": "text/event-stream",
        [REQUEST_ID_HEADER]: "req-trace-stream-001",
      },
    });
  }
  if (path === "/api/papers" && request.method === "GET") {
    if (scenario === "emptyPapers") return json(EMPTY_PAPER_RESULTS);
    if (scenario === "error") {
      return json(ERROR_BODY, 503);
    }
    return json({ results: PAPER_RESULTS });
  }
  if (path.startsWith("/api/images/") && request.method === "GET") {
    const pixel = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
      "base64",
    );
    return new Response(pixel, { status: 200, headers: { "content-type": "image/png" } });
  }
  if (scenario === "error") {
    return new Response(JSON.stringify(ERROR_BODY), {
      status: 503,
      headers: { ...jsonHeaders, [REQUEST_ID_HEADER]: "req-error-503" },
    });
  }

  // Unmatched calls are loud: a test must never silently fall through to a network request.
  throw new Error(`No mock handler for ${request.method} ${path} (scenario: ${scenario})`);
}
