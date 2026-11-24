import { describe, expect, it } from "vitest";

import coreEmitted from "./mocks/core-emitted.json";
import { ApiError } from "./errors";
import {
  AnswerSchema,
  CitationSchema,
  ImageRefSchema,
  PastPaperQuestionSchema,
  parseOrThrow,
  QuerySchema,
} from "./schemas";

/** Serialize back to plain JSON so defaults/nulls are compared, not prototypes. */
function roundTrip<T>(value: T): unknown {
  return JSON.parse(JSON.stringify(value)) as unknown;
}

describe("frozen-schema mirror fidelity", () => {
  it("round-trips JSON emitted by the core Query model", () => {
    expect(roundTrip(QuerySchema.parse(coreEmitted.query))).toEqual(coreEmitted.query);
  });

  it("round-trips JSON emitted by the core Citation model", () => {
    expect(roundTrip(CitationSchema.parse(coreEmitted.citation))).toEqual(coreEmitted.citation);
  });

  it("round-trips JSON emitted by the core ImageRef model", () => {
    expect(roundTrip(ImageRefSchema.parse(coreEmitted.image_ref))).toEqual(coreEmitted.image_ref);
  });

  it("round-trips JSON emitted by the core Answer model with citations and images", () => {
    expect(roundTrip(AnswerSchema.parse(coreEmitted.answer))).toEqual(coreEmitted.answer);
  });

  it("round-trips JSON emitted by the core PastPaperQuestion model", () => {
    expect(roundTrip(PastPaperQuestionSchema.parse(coreEmitted.past_paper))).toEqual(
      coreEmitted.past_paper,
    );
  });

  it("round-trips an abstaining answer emitted by core", () => {
    expect(roundTrip(AnswerSchema.parse(coreEmitted.abstained_answer))).toEqual(
      coreEmitted.abstained_answer,
    );
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

  it("rejects an extra field the core model would forbid", () => {
    expect(
      AnswerSchema.safeParse({ ...coreEmitted.answer, invented_field: true }).success,
    ).toBe(false);
  });
});
