/** Live API client. Every response is validated at the edge (AGENT.md §4). */

import { ApiError, httpErrorFrom, logClientError, requestIdFrom } from "./errors";
import { ROUTES } from "./routes";
import { filtersToQueryString, type PaperFilters } from "../filters";
import {
  AnswerSchema,
  CitationsEventSchema,
  FeedbackRequestSchema,
  FeedbackResponseSchema,
  PaperSearchResultSchema,
  parseOrThrow,
  QuerySchema,
  TokenEventSchema,
  type Answer,
  type FeedbackRequest,
  type FeedbackResponse,
  type PaperSearchResult,
  type Query,
} from "./schemas";
import { parseSseStream } from "./sse";

const DEFAULT_TIMEOUT_MS = 10_000;
const STREAM_TIMEOUT_MS = 60_000;

/** The only incremental callback the real SSE stream supports. */
export type StreamHandlers = {
  onToken(text: string): void;
};

/** ADR 0009: 202 echoes the validated payload and carries a trace id. */
export type FeedbackResult = {
  accepted: true;
  requestId: string | null;
  response: FeedbackResponse;
};

type JsonResponse = { status: number; requestId: string | null; body: unknown };

/** Fetch JSON with a timeout; non-2xx becomes a typed, trace-correlated error. */
async function requestJson(path: string, init: RequestInit): Promise<JsonResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
  try {
    const response = await fetch(path, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(init.headers as Record<string, string> | undefined),
      },
    });
    if (!response.ok) throw await httpErrorFrom(response, path);
    const requestId = requestIdFrom(response.headers);
    const body: unknown =
      response.status === 204
        ? null
        : await response.json().catch(() => {
            throw new ApiError(
              "Malformed JSON response",
              "http",
              response.status,
              requestId,
              "invalid_json_response",
            );
          });
    return { status: response.status, requestId, body };
  } finally {
    clearTimeout(timeout);
  }
}

/** Submit a validated Query to POST /api/v1/query and receive a validated Answer. */
export async function query(query: Query): Promise<Answer> {
  const body = QuerySchema.parse(query);
  const response = await requestJson(ROUTES.query, {
    method: "POST",
    body: JSON.stringify(body),
  });
  return parseOrThrow(AnswerSchema, response.body, "answer");
}

/** POST /api/v1/feedback: 202 success, 422 typed error, both with x-request-id. */
export async function feedback(request: FeedbackRequest): Promise<FeedbackResult> {
  const body = FeedbackRequestSchema.parse(request);
  const response = await requestJson(ROUTES.feedback, {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (response.status !== 202) {
    throw new ApiError(
      "Feedback endpoint did not return 202",
      "http",
      response.status,
      response.requestId,
      "unexpected_feedback_status",
    );
  }
  return {
    accepted: true,
    requestId: response.requestId,
    response: parseOrThrow(FeedbackResponseSchema, response.body, "feedback response"),
  };
}

/**
 * GET /api/v1/papers: strict artifact `PaperSearchResult` with payload-carried
 * last_crawled provenance; no match is `{"results": []}` with 200. 422/503 are typed
 * `ApiError`s carrying the response's x-request-id.
 */
export async function papers(filters: PaperFilters): Promise<PaperSearchResult> {
  const queryString = filtersToQueryString(filters);
  const path = queryString === "" ? ROUTES.papers : `${ROUTES.papers}?${queryString}`;
  const response = await requestJson(path, { method: "GET" });
  return parseOrThrow(PaperSearchResultSchema, response.body, "papers");
}

/**
 * Consume the real SSE stream: `token` frames (`TokenEvent`) and one final
 * `citations` frame (`CitationsEvent`) carrying the authoritative Answer.
 * A malformed event, an unknown event name or a missing final citations frame
 * is a typed ApiError — never a partial render (L11).
 */
export async function stream(query: Query, handlers: StreamHandlers): Promise<Answer> {
  const body = QuerySchema.parse(query);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), STREAM_TIMEOUT_MS);
  try {
    return await consumeStream(body, handlers, controller.signal);
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") {
      const error = new ApiError("Stream timed out", "stream", 0, null, "stream_timeout");
      logClientError(error, "client.stream");
      throw error;
    }
    throw cause;
  } finally {
    clearTimeout(timeout);
  }
}

async function consumeStream(
  body: Query,
  handlers: StreamHandlers,
  signal: AbortSignal,
): Promise<Answer> {
  const response = await fetch(ROUTES.stream, {
    method: "POST",
    headers: { Accept: "text/event-stream", "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok) throw await httpErrorFrom(response, ROUTES.stream);
  if (!response.body) {
    throw new ApiError("Stream response had no body", "stream", 0, requestIdFrom(response.headers));
  }

  const requestId = requestIdFrom(response.headers);
  let committed: Answer | null = null;

  for await (const event of parseSseStream(response.body)) {
    let payload: unknown;
    try {
      payload = JSON.parse(event.data);
    } catch {
      const malformed = new ApiError(
        "Malformed SSE event JSON",
        "stream",
        0,
        requestId,
        "invalid_stream_json",
      );
      logClientError(malformed, "client.stream");
      throw malformed;
    }

    switch (event.event) {
      case "token": {
        handlers.onToken(parseOrThrow(TokenEventSchema, payload, "token event").token);
        break;
      }
      case "citations": {
        committed = parseOrThrow(CitationsEventSchema, payload, "citations event").answer;
        break;
      }
      default: {
        const error = new ApiError(
          `Unknown stream event: ${event.event}`,
          "stream",
          0,
          requestId,
          "unknown_stream_event",
        );
        logClientError(error, "client.stream");
        throw error;
      }
    }
  }

  if (committed === null) {
    const error = new ApiError(
      "Stream ended without a final citations event",
      "stream",
      0,
      requestId,
      "missing_citations_event",
    );
    logClientError(error, "client.stream");
    throw error;
  }
  return committed;
}
