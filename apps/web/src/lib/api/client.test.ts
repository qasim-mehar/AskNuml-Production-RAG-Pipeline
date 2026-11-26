import { describe, expect, it, vi } from "vitest";

import contract from "./mocks/openapi-emitted.json";
import {
  CITATION,
  EMPTY_PAPER_RESULTS,
  ENGLISH_ANSWER,
  ERROR_BODY,
  FEEDBACK_REQUEST,
  PAPER_LAST_CRAWLED,
  PAPER_VALIDATION_ERROR,
  STREAM_EVENTS,
} from "./mocks/fixtures";
import { lastMockCall, setMockScenario, STREAM_TICK_MS } from "./mocks/handlers";
import { feedback, papers, query, stream } from "./client";
import { requestIdFrom } from "./errors";
import { EMPTY_FILTERS } from "../filters";
import type { Query } from "./schemas";

const TEST_QUERY: Query = {
  query_id: "q-test",
  text: "What is the fee?",
  language: "en",
  top_k: 10,
  filters: {},
};

function pathOf(url: string | undefined): string {
  return new URL(url ?? "http://localhost/").pathname;
}

describe("live API client routes and edge validation", () => {
  it("posts a Query to the artifact route and preserves real citation provenance", async () => {
    setMockScenario("english");
    const answer = await query(TEST_QUERY);

    expect(pathOf(lastMockCall()?.url)).toBe(contract.routes.query);
    expect(lastMockCall()?.method).toBe("POST");
    expect(lastMockCall()?.body).toMatchObject({ query_id: "q-test", language: "en" });
    expect(answer.answer_id).toBe(ENGLISH_ANSWER.answer_id);
    expect(answer.citations[0]?.last_crawled).toBe(CITATION.last_crawled);
    expect(answer.images[0]?.image_url).toBeNull();
  });

  it("accepts feedback 202, echoes the payload and captures x-request-id", async () => {
    setMockScenario("english");
    const result = await feedback({ ...FEEDBACK_REQUEST });

    expect(pathOf(lastMockCall()?.url)).toBe(contract.conventions.feedback);
    expect(lastMockCall()?.method).toBe("POST");
    expect(lastMockCall()?.body).toEqual(FEEDBACK_REQUEST);
    expect(result).toMatchObject({
      accepted: true,
      requestId: "req-feedback-202",
      response: FEEDBACK_REQUEST,
    });
  });

  it("surfaces feedback 422 as a typed error with its own request id", async () => {
    setMockScenario("feedback422");
    await expect(feedback(FEEDBACK_REQUEST)).rejects.toMatchObject({
      kind: "http",
      status: 422,
      code: "validation_error",
      requestId: "req-feedback-422",
    });
  });

  it("rejects a feedback response that is not the ADR 0009 202", async () => {
    setMockScenario("feedback200");
    await expect(feedback(FEEDBACK_REQUEST)).rejects.toMatchObject({
      kind: "http",
      code: "unexpected_feedback_status",
      requestId: "req-feedback-200",
    });
  });

  it("encodes Urdu department names in the finder query", async () => {
    setMockScenario("papers");
    const result = await papers({
      courseCode: "CS",
      year: "2024",
      term: "fall",
      examType: "final",
      department: "کمپیوٹر سائنس",
    });
    const url = new URL(lastMockCall()?.url ?? "http://localhost/");

    expect(pathOf(url.toString())).toBe(contract.routes.papers);
    const params = Object.fromEntries(url.searchParams);
    expect(contract.papers.pagination).toEqual(["limit", "offset"]);
    expect(Object.keys(params)).toEqual(contract.papers.filters);
    expect(params).toEqual({
      course_code: "CS",
      year: "2024",
      term: "fall",
      exam_type: "final",
      department: "کمپیوٹر سائنس",
    });
    expect(result.results[0]?.course_code).toBe("CS");
    expect(result.results[0]?.last_crawled).toBe(PAPER_LAST_CRAWLED);
  });

  it("returns the artifact's empty {results: []} shape on no match", async () => {
    setMockScenario("emptyPapers");
    const result = await papers(EMPTY_FILTERS);

    expect(result).toEqual(contract.papers.empty);
    expect(result).toEqual(EMPTY_PAPER_RESULTS);
  });

  it("surfaces papers 422 and 503 as typed errors with their own request ids", async () => {
    expect(contract.papers.errorStatuses).toEqual(expect.arrayContaining(["422", "503"]));

    setMockScenario("papers422");
    await expect(papers(EMPTY_FILTERS)).rejects.toMatchObject({
      kind: "http",
      status: 422,
      code: PAPER_VALIDATION_ERROR.code,
      requestId: "req-papers-422",
    });

    setMockScenario("papers503");
    await expect(papers(EMPTY_FILTERS)).rejects.toMatchObject({
      kind: "http",
      status: 503,
      code: ERROR_BODY.code,
      message: ERROR_BODY.message,
      requestId: "req-papers-503",
    });
  });

  it("reads the artifact-declared x-request-id from a finder response", () => {
    const header = contract.papers.requestIdHeader;
    expect(header).toBe("x-request-id");
    const response = new Response(null, { headers: { [header]: "req-papers-200" } });
    expect(requestIdFrom(response.headers)).toBe("req-papers-200");
  });

  it("surfaces a typed HTTP error carrying the trace request id", async () => {
    setMockScenario("error");
    await expect(query(TEST_QUERY)).rejects.toMatchObject({
      kind: "http",
      status: 503,
      requestId: "req-error-503",
      message: ERROR_BODY.message,
    });
  });

  it("rejects a schema-mismatched payload with a typed error", async () => {
    setMockScenario("invalid");
    await expect(query(TEST_QUERY)).rejects.toMatchObject({
      kind: "schema",
      code: "schema_validation_failed",
    });
  });

  it("streams tokens incrementally and commits a real citations envelope with last_crawled", async () => {
    vi.useFakeTimers();
    setMockScenario("stream");
    const tokens: string[] = [];

    const settled = stream(TEST_QUERY, { onToken: (token) => tokens.push(token) });
    await vi.advanceTimersByTimeAsync(STREAM_TICK_MS);
    expect(tokens.join("")).not.toBe("");
    expect(tokens.join("")).not.toBe(ENGLISH_ANSWER.text);

    await vi.runAllTimersAsync();
    const answer = await settled;

    expect(pathOf(lastMockCall()?.url)).toBe(contract.routes.stream);
    expect(tokens.join("")).toBe(ENGLISH_ANSWER.text);
    expect(STREAM_EVENTS.at(-1)?.event).toBe("citations");
    expect(answer.answer_id).toBe(ENGLISH_ANSWER.answer_id);
    expect(answer.citations[0]?.last_crawled).toBe(CITATION.last_crawled);
    expect(answer.images[0]?.ref_id).toBe(ENGLISH_ANSWER.images[0]?.ref_id);
  });

  it("rejects a final citations event whose Answer fails schema validation", async () => {
    setMockScenario("invalidStream");
    vi.useFakeTimers();
    const settled = stream(TEST_QUERY, { onToken: () => undefined });
    const rejection = expect(settled).rejects.toMatchObject({ kind: "schema" });
    await vi.runAllTimersAsync();
    await rejection;
  });

  it("surfaces an unknown SSE event as a typed error instead of a partial render", async () => {
    setMockScenario("unknownStream");
    vi.useFakeTimers();
    const settled = stream(TEST_QUERY, { onToken: () => undefined });
    const rejection = expect(settled).rejects.toMatchObject({
      kind: "stream",
      code: "unknown_stream_event",
    });
    await vi.runAllTimersAsync();
    await rejection;
  });

  it("surfaces a stream HTTP error envelope with its trace id", async () => {
    setMockScenario("error");
    await expect(stream(TEST_QUERY, { onToken: () => undefined })).rejects.toMatchObject({
      kind: "http",
      status: 503,
      requestId: "req-error-stream-503",
    });
  });
});
