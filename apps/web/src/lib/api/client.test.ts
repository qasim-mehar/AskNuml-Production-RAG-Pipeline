import type { Citation } from "./schemas";
import { describe, expect, it, vi } from "vitest";

import {
  CITATION,
  ENGLISH_ANSWER,
  ERROR_BODY,
  STREAM_EVENTS,
} from "./mocks/fixtures";
import {
  lastMockCall,
  setMockScenario,
  STREAM_TICK_MS,
} from "./mocks/handlers";
import { feedback, papers, query, stream } from "./client";
import type { Query } from "./schemas";

const TEST_QUERY: Query = {
  query_id: "q-test",
  text: "What is the fee?",
  language: "en",
  top_k: 10,
  filters: {},
};

describe("typed API client", () => {
  it("validates a query response at the edge", async () => {
    setMockScenario("english");
    const answer = await query(TEST_QUERY);
    expect(answer.answer_id).toBe(ENGLISH_ANSWER.answer_id);
    expect(lastMockCall()?.url).toContain("/api/query");
    expect(lastMockCall()?.body).toMatchObject({ query_id: "q-test", language: "en" });
  });

  it("posts feedback with the answer id and sentiment", async () => {
    setMockScenario("english");
    await feedback({ answer_id: "answer-en-1", sentiment: "negative", reason: "too vague" });
    expect(lastMockCall()?.url).toContain("/api/feedback");
    expect(lastMockCall()?.body).toEqual({
      answer_id: "answer-en-1",
      sentiment: "negative",
      reason: "too vague",
    });
  });

  it("encodes Urdu department names in the finder query", async () => {
    setMockScenario("papers");
    await papers({
      courseCode: "CS",
      year: "2024",
      term: "fall",
      examType: "final",
      department: "کمپیوٹر سائنس",
    });
    const url = new URL(lastMockCall()?.url ?? "http://localhost/");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      course_code: "CS",
      year: "2024",
      term: "fall",
      exam_type: "final",
      department: "کمپیوٹر سائنس",
    });
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

  it("streams tokens incrementally and validates every event", async () => {
    vi.useFakeTimers();
    setMockScenario("stream");
    const tokens: string[] = [];
    const citations: Citation[] = [];
    const images: string[] = [];

    const settled = stream(TEST_QUERY, {
      onToken: (token) => tokens.push(token),
      onCitation: (citation) => citations.push(citation),
      onImage: (image) => images.push(image.ref_id),
    });

    await vi.advanceTimersByTimeAsync(STREAM_TICK_MS);
    expect(tokens.join("")).not.toBe("");
    expect(tokens.join("")).not.toBe(ENGLISH_ANSWER.text);

    await vi.runAllTimersAsync();
    const answer = await settled;

    expect(tokens.join("")).toBe(ENGLISH_ANSWER.text);
    expect(citations).toEqual([CITATION]);
    expect(images).toEqual(["past-2024-cs-p2"]);
    expect(answer.answer_id).toBe(ENGLISH_ANSWER.answer_id);
    expect(answer.citations[0]?.source_url).toBe(CITATION.source_url);
    expect(STREAM_EVENTS.length).toBeGreaterThan(tokens.length);
  });

  it("rejects a stream whose final answer fails schema validation", async () => {
    setMockScenario("invalidStream");
    vi.useFakeTimers();
    const settled = stream(TEST_QUERY, {
      onToken: () => undefined,
      onCitation: () => undefined,
      onImage: () => undefined,
    });
    const rejection = expect(settled).rejects.toMatchObject({ kind: "schema" });
    await vi.runAllTimersAsync();
    await rejection;
  });
});
