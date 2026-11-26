import { describe, expect, it } from "vitest";

import coreEmitted from "./mocks/core-emitted.json";
import openapiEmitted from "./mocks/openapi-emitted.json";
import { ApiError } from "./errors";
import {
  AnswerSchema,
  CitationsEventSchema,
  CitationSchema,
  ErrorBodySchema,
  FeedbackResponseSchema,
  ImageRefSchema,
  PaperRecordSchema,
  PaperSearchResultSchema,
  PastPaperQuestionSchema,
  parseOrThrow,
  QuerySchema,
  TokenEventSchema,
} from "./schemas";

/** Serialize back to plain JSON so defaults/nulls are compared, not prototypes. */
function roundTrip<T>(value: T): unknown {
  return JSON.parse(JSON.stringify(value)) as unknown;
}

describe("core-emitted mirror fidelity (ADR 0007 fields)", () => {
  it("round-trips the core Query model", () => {
    expect(roundTrip(QuerySchema.parse(coreEmitted.query))).toEqual(coreEmitted.query);
  });

  it("round-trips a Citation carrying real last_crawled", () => {
    expect(coreEmitted.citation.last_crawled).toBe("2026-11-20T09:30:00Z");
    expect(roundTrip(CitationSchema.parse(coreEmitted.citation))).toEqual(coreEmitted.citation);
  });

  it("round-trips an ImageRef carrying a real image_url", () => {
    expect(coreEmitted.image_ref.image_url).toBe("/api/images/img-1");
    expect(roundTrip(ImageRefSchema.parse(coreEmitted.image_ref))).toEqual(coreEmitted.image_ref);
  });

  it("round-trips an Answer with provenance and abstention fields", () => {
    expect(roundTrip(AnswerSchema.parse(coreEmitted.answer))).toEqual(coreEmitted.answer);
  });

  it("round-trips a PastPaperQuestion with ADR 0007 finder fields", () => {
    expect(roundTrip(PastPaperQuestionSchema.parse(coreEmitted.past_paper))).toEqual(
      coreEmitted.past_paper,
    );
  });

  it("round-trips a PaperRecord carrying the artifact's required last_crawled", () => {
    expect(coreEmitted.paper_record.last_crawled).toBe("2026-11-20T09:30:00Z");
    expect(roundTrip(PaperRecordSchema.parse(coreEmitted.paper_record))).toEqual(
      coreEmitted.paper_record,
    );
  });

  it("round-trips an abstaining answer emitted by core", () => {
    expect(roundTrip(AnswerSchema.parse(coreEmitted.abstained_answer))).toEqual(
      coreEmitted.abstained_answer,
    );
  });
});

describe("OpenAPI artifact alignment", () => {
  it("round-trips every generated artifact payload through its Zod mirror", () => {
    const payloads = openapiEmitted.payloads;
    expect(roundTrip(QuerySchema.parse(payloads.Query))).toEqual(payloads.Query);
    expect(roundTrip(CitationSchema.parse(payloads.Citation))).toEqual(payloads.Citation);
    expect(roundTrip(ImageRefSchema.parse(payloads.ImageRef))).toEqual(payloads.ImageRef);
    expect(roundTrip(AnswerSchema.parse(payloads.Answer))).toEqual(payloads.Answer);
    expect(roundTrip(ErrorBodySchema.parse(payloads.ErrorBody))).toEqual(payloads.ErrorBody);
    expect(roundTrip(PaperRecordSchema.parse(payloads.PaperRecord))).toEqual(payloads.PaperRecord);
    expect(roundTrip(PaperSearchResultSchema.parse(payloads.PaperSearchResult))).toEqual(
      payloads.PaperSearchResult,
    );
  });

  it("accepts the artifact's empty finder result and its declared error statuses", () => {
    expect(openapiEmitted.papers.operationId).toBe("find_papers_api_v1_papers_get");
    expect(openapiEmitted.papers.empty).toEqual({ results: [] });
    expect(roundTrip(PaperSearchResultSchema.parse(openapiEmitted.papers.empty))).toEqual({
      results: [],
    });
    expect(openapiEmitted.papers.errorStatuses).toEqual(expect.arrayContaining(["422", "503"]));
    expect(openapiEmitted.papers.requestIdHeader).toBe("x-request-id");
  });

  it("accepts the API-local SSE envelopes and rejects unknown shapes", () => {
    const answer = AnswerSchema.parse(openapiEmitted.payloads.Answer);
    expect(CitationsEventSchema.parse({ answer }).answer.answer_id).toBe(answer.answer_id);
    expect(TokenEventSchema.parse({ token: " crescent " }).token).toBe(" crescent ");
    expect(CitationsEventSchema.safeParse({ type: "answer", answer }).success).toBe(false);
  });

  it("accepts the ADR 0009 feedback echo and rejects unknown fields", () => {
    const echo = { answer_id: "a-1", sentiment: "positive", reason: "clear" };
    expect(FeedbackResponseSchema.parse(echo)).toEqual(echo);
    expect(FeedbackResponseSchema.safeParse({ ...echo, persisted: true }).success).toBe(false);
  });
});

describe("strict edge validation", () => {
  it("rejects an unsupported language with a typed schema error", () => {
    expect(() =>
      parseOrThrow(AnswerSchema, { ...coreEmitted.answer, language: "fr" }, "answer"),
    ).toThrowError(ApiError);
    try {
      parseOrThrow(AnswerSchema, { ...coreEmitted.answer, language: "fr" }, "answer");
    } catch (cause) {
      expect(cause).toMatchObject({ kind: "schema", code: "schema_validation_failed" });
    }
  });

  it("rejects an extra field the artifact forbids", () => {
    expect(
      AnswerSchema.safeParse({ ...coreEmitted.answer, invented_field: true }).success,
    ).toBe(false);
  });

  it("requires last_crawled on a PaperRecord and forbids unknown fields", () => {
    expect(PaperRecordSchema.safeParse(coreEmitted.past_paper).success).toBe(false);
    expect(
      PaperRecordSchema.safeParse({
        ...coreEmitted.paper_record,
        invented_field: true,
      }).success,
    ).toBe(false);
    expect(
      PaperSearchResultSchema.safeParse({ results: [], invented_field: true }).success,
    ).toBe(false);
    expect(
      PaperRecordSchema.safeParse({
        ...coreEmitted.paper_record,
        last_crawled: "not-a-date",
      }).success,
    ).toBe(false);
  });
});
