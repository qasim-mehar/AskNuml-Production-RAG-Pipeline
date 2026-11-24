import { z } from "zod";

import { ApiError } from "./errors";

/**
 * TypeScript mirrors of the frozen core schemas. Source of truth:
 * packages/core/src/uni_rag_core/schemas/{query,answer,chunk,enums,past_paper}.py
 * (Pydantic v2, extra="forbid", frozen). These objects are strict: an unknown
 * field is rejected, never carried into the UI. Fidelity is pinned by
 * `schemas.test.ts` against `mocks/core-emitted.json`, which is generated from
 * the Pydantic models themselves.
 */

function parseOrThrow<T>(schema: z.ZodType<T>, value: unknown, field: string): T {
  const result = schema.safeParse(value);
  if (!result.success) {
    throw new ApiError(
      `Invalid ${field} payload: ${result.error.issues[0]?.message ?? "schema mismatch"}`,
      "schema",
      0,
      null,
      "schema_validation_failed",
    );
  }
  return result.data;
}

export const LanguageSchema = z.enum(["en", "ur", "roman_urdu"]);
export type Language = z.infer<typeof LanguageSchema>;

export const ImageRefSchema = z
  .object({
    ref_id: z.string(),
    source_url: z.string(),
    page: z.number().int().nullable().default(null),
    caption: z.string().nullable().default(null),
    mime_type: z.string().default("image/png"),
  })
  .strict();
export type ImageRef = z.infer<typeof ImageRefSchema>;

export const CitationSchema = z
  .object({
    chunk_id: z.string(),
    doc_id: z.string(),
    source_url: z.string(),
    snippet: z.string(),
    page: z.number().int().nullable().default(null),
    score: z.number().nullable().default(null),
    /**
     * Forward-compatible only: the frozen core `Citation` has no last-crawled
     * field. A chip renders this verbatim when a payload carries it and renders
     * nothing otherwise. Lane 0 must merge a CONTRACT-CHANGE to core before
     * Lane G may emit it (see handoff).
     */
    last_crawled: z.string().nullable().optional(),
  })
  .strict();
export type Citation = z.infer<typeof CitationSchema>;

export const AnswerSchema = z
  .object({
    answer_id: z.string(),
    query_id: z.string(),
    text: z.string(),
    citations: z.array(CitationSchema).default([]),
    images: z.array(ImageRefSchema).default([]),
    abstained: z.boolean().default(false),
    confidence: z.number().default(0),
    language: LanguageSchema.default("en"),
  })
  .strict();
export type Answer = z.infer<typeof AnswerSchema>;

export const QuerySchema = z
  .object({
    query_id: z.string(),
    text: z.string(),
    language: LanguageSchema,
    top_k: z.number().int().default(10),
    filters: z.record(z.string(), z.string()).default({}),
  })
  .strict();
export type Query = z.infer<typeof QuerySchema>;

export const PastPaperQuestionSchema = z
  .object({
    question_id: z.string(),
    doc_id: z.string(),
    source_url: z.string(),
    page: z.number().int(),
    question_number: z.number().int(),
    text: z.string(),
    year: z.number().int().nullable().default(null),
    subject: z.string().nullable().default(null),
    options: z.array(z.string()).default([]),
    image_ref: ImageRefSchema.nullable().default(null),
  })
  .strict();
export type PastPaperQuestion = z.infer<typeof PastPaperQuestionSchema>;

/** Lane G contract expectation: the finder response envelope. */
export const PaperSearchResultSchema = z
  .object({ results: z.array(PastPaperQuestionSchema) })
  .strict();
export type PaperSearchResult = z.infer<typeof PaperSearchResultSchema>;

/** Lane G contract expectation: feedback has no frozen core schema yet. */
export const SentimentSchema = z.enum(["positive", "negative"]);
export type Sentiment = z.infer<typeof SentimentSchema>;

export const FeedbackRequestSchema = z
  .object({
    answer_id: z.string(),
    query_id: z.string().optional(),
    sentiment: SentimentSchema,
    reason: z.string().optional(),
  })
  .strict();
export type FeedbackRequest = z.infer<typeof FeedbackRequestSchema>;

/** The SSE event contract consumed by the streaming client. */
export const TokenEventSchema = z.strictObject({
  type: z.literal("token"),
  text: z.string(),
});
export const CitationEventSchema = z.strictObject({
  type: z.literal("citation"),
  citation: CitationSchema,
});
export const ImageEventSchema = z.strictObject({
  type: z.literal("image"),
  image: ImageRefSchema,
});
export const AnswerEventSchema = z.strictObject({
  type: z.literal("answer"),
  answer: AnswerSchema,
});
export const StreamErrorEventSchema = z.strictObject({
  type: z.literal("error"),
  code: z.string(),
  message: z.string(),
});

export { parseOrThrow };
