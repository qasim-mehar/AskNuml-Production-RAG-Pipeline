import { z } from "zod";

import { ApiError } from "./errors";

/**
 * Strict TypeScript mirrors of every payload Web reads at the edge.
 * Source of truth: `apps/api/openapi.json` (served artifact) plus the frozen
 * core Pydantic models for `PastPaperQuestion`; the artifact's `PaperRecord`
 * adds the required `last_crawled` provenance field (ADR 0011).
 * Fidelity is pinned by `schemas.test.ts`, which round-trips both generated
 * fixtures (`mocks/core-emitted.json`, `mocks/openapi-emitted.json`) through
 * these mirrors. Unknown fields are rejected, never carried into the UI.
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
    /** ADR 0007: real, optional field. The route convention is the fallback. */
    image_url: z.string().nullable().default(null),
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
    /** ADR 0007: real, optional provenance field — formatted for display or omitted. */
    last_crawled: z.string().nullable().default(null),
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
    next_step: z.string().nullable().default(null),
    abstention_reason: z.string().nullable().default(null),
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

/** ErrorBody is served on every non-2xx response, including 422 feedback. */
export const ErrorBodySchema = z
  .object({
    code: z.string(),
    message: z.string(),
    details: z.record(z.string(), z.unknown()).default({}),
  })
  .strict();
export type ErrorBody = z.infer<typeof ErrorBodySchema>;

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
    // ADR 0007 finder fields from core; the artifact's PaperRecord adds
    // required last_crawled provenance on top of this datum (ADR 0011).
    course_code: z.string().nullable().default(null),
    term: z.string().nullable().default(null),
    exam_type: z.string().nullable().default(null),
    department: z.string().nullable().default(null),
  })
  .strict();
export type PastPaperQuestion = z.infer<typeof PastPaperQuestionSchema>;

/**
 * Artifact `PaperRecord`: the core question fields plus the frozen crawl time.
 * Required as a date-time string in the artifact; never reconstructed by Web.
 */
export const PaperRecordSchema = PastPaperQuestionSchema.extend({
  // Artifact format: date-time; accept both `Z` and explicit UTC offsets.
  last_crawled: z.iso.datetime({ offset: true }),
}).strict();
export type PaperRecord = z.infer<typeof PaperRecordSchema>;

/** Artifact `PaperSearchResult`: strict `{results: PaperRecord[]}`; no match is `[]`. */
export const PaperSearchResultSchema = z
  .object({ results: z.array(PaperRecordSchema) })
  .strict();
export type PaperSearchResult = z.infer<typeof PaperSearchResultSchema>;

/** ADR 0009: strict feedback request and the 202 body that echoes it. */
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

export const FeedbackResponseSchema = FeedbackRequestSchema;
export type FeedbackResponse = z.infer<typeof FeedbackResponseSchema>;

/**
 * API-local SSE envelopes from `uni_rag_api.schemas` (ADR 0009 keeps them out
 * of core). The stream emits `token` frames and one final `citations` frame
 * carrying the authoritative Answer. Every other event name is a typed error.
 */
export const TokenEventSchema = z.strictObject({ token: z.string() });
export const CitationsEventSchema = z.strictObject({ answer: AnswerSchema });

export { parseOrThrow };
