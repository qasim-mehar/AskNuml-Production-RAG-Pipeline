import { fetchJson } from "../api-client";
import { filtersToQueryString, type PaperFilters } from "../filters";
import { ApiError, httpErrorFrom, logClientError, requestIdFrom } from "./errors";
import {
  AnswerEventSchema,
  AnswerSchema,
  CitationEventSchema,
  FeedbackRequestSchema,
  ImageEventSchema,
  type Answer,
  type Citation,
  type FeedbackRequest,
  type ImageRef,
  type Query,
  QuerySchema,
  type PaperSearchResult,
  PaperSearchResultSchema,
  parseOrThrow,
  StreamErrorEventSchema,
  TokenEventSchema,
} from "./schemas";
import { parseSseStream } from "./sse";

const API_BASE = "/api";

/** Incremental callbacks the chat hook uses to render a streamed answer. */
export type StreamHandlers = {
  onToken(text: string): void;
  onCitation(citation: Citation): void;
  onImage(image: ImageRef): void;
};

/** POST JSON and return the parsed body plus the API trace header. */
async function postJson(path: string, body: unknown): Promise<unknown> {
  const response = await fetch(path, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw await httpErrorFrom(response, path);
  if (response.status === 204) return null;
  try {
    return await response.json();
  } catch {
    throw new ApiError(
      "Malformed JSON response",
      "http",
      response.status,
      requestIdFrom(response.headers),
      "invalid_json_response",
    );
  }
}

/** Submit a validated Query and receive a fully validated Answer. */
export async function query(query: Query): Promise<Answer> {
  const body = QuerySchema.parse(query);
  const raw = await postJson(`${API_BASE}/query`, body);
  return parseOrThrow(AnswerSchema, raw, "answer");
}

/** Send feedback for one answer. Lane G must accept this envelope (see handoff). */
export async function feedback(request: FeedbackRequest): Promise<void> {
  const body = FeedbackRequestSchema.parse(request);
  await postJson(`${API_BASE}/feedback`, body);
}

/** Look up past papers; every result is schema-validated before it reaches the UI. */
export async function papers(filters: PaperFilters): Promise<PaperSearchResult> {
  const path = `${API_BASE}/papers?${filtersToQueryString(filters)}`;
  const raw: unknown = await fetchJson(path);
  return parseOrThrow(PaperSearchResultSchema, raw, "papers");
}

/**
 * Consume an SSE answer stream. Each event is validated at the edge; the final
 * `answer` event is authoritative. A malformed event or a stream that ends
 * without a final answer throws a typed ApiError — never a partial render.
 */
export async function stream(query: Query, handlers: StreamHandlers): Promise<Answer> {
  const body = QuerySchema.parse(query);
  const response = await fetch(`${API_BASE}/query/stream`, {
    method: "POST",
    headers: { Accept: "text/event-stream", "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw await httpErrorFrom(response, "/api/query/stream");
  if (!response.body) {
    throw new ApiError("Stream response had no body", "stream", 0, requestIdFrom(response.headers));
  }

  let committed: Answer | null = null;
  const requestId = requestIdFrom(response.headers);

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
        const parsed = parseOrThrow(TokenEventSchema, payload, "token event");
        handlers.onToken(parsed.text);
        break;
      }
      case "citation": {
        const parsed = parseOrThrow(CitationEventSchema, payload, "citation event");
        handlers.onCitation(parsed.citation);
        break;
      }
      case "image": {
        const parsed = parseOrThrow(ImageEventSchema, payload, "image event");
        handlers.onImage(parsed.image);
        break;
      }
      case "answer": {
        committed = parseOrThrow(AnswerEventSchema, payload, "answer event").answer;
        break;
      }
      case "error": {
        const parsed = parseOrThrow(StreamErrorEventSchema, payload, "stream error event");
        const streamError = new ApiError(parsed.message, "stream", 0, requestId, parsed.code);
        logClientError(streamError, "client.stream");
        throw streamError;
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
      "Stream ended without a final answer event",
      "stream",
      0,
      requestId,
      "missing_answer_event",
    );
    logClientError(error, "client.stream");
    throw error;
  }
  return committed;
}
