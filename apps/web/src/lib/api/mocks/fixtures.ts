/**
 * Deterministic payload corpus for the live client. Values are hand-written
 * test data; their shapes mirror the generated contract fixtures
 * (`core-emitted.json`, `openapi-emitted.json`), ADR 0007/0009 and the
 * API-local SSE envelopes in `uni_rag_api.schemas`. `schemas.test.ts` pins
 * that alignment by round-tripping both generated fixtures through the Zod
 * mirrors. No fixture invents provenance the payload does not carry (L5).
 */

import type { Answer, Citation, FeedbackResponse, ImageRef, PaperRecord } from "../schemas";

/** Frozen crawl timestamp carried by every paper fixture (L4, L5). */
export const PAPER_LAST_CRAWLED = "2026-11-20T09:30:00Z";

/** Fallback case: no image_url, so the client must use /api/images/{ref_id}. */
export const IMAGE_REF: ImageRef = {
  ref_id: "past-2024-cs-p2",
  source_url: "https://uni.example/archive/cs-2024-final.pdf",
  page: 2,
  caption: "Past paper page 2",
  mime_type: "image/png",
  image_url: null,
};

/** ADR 0007 case: the payload carries its own browser-fetchable URL. */
export const IMAGE_REF_WITH_URL: ImageRef = {
  ...IMAGE_REF,
  ref_id: "past-2024-cs-p2-url",
  image_url: "/api/images/past-2024-cs-p2-url",
};

export const CITATION: Citation = {
  chunk_id: "chunk-fee-1",
  doc_id: "doc-fee",
  source_url: "https://uni.example/admissions/fees",
  snippet: "BSc Computer Science tuition is 1000 USD per semester.",
  page: 3,
  score: 0.91,
  last_crawled: "2026-11-20T09:30:00Z",
};

export const URDU_CITATION: Citation = {
  chunk_id: "chunk-fee-ur-1",
  doc_id: "doc-fee-ur",
  source_url: "https://uni.example/admissions/fees/ur",
  snippet: "کمپیوٹر سائنس کی فیس 1000 ڈالر ہے۔",
  page: null,
  score: null,
  last_crawled: null,
};

export const ENGLISH_ANSWER: Answer = {
  answer_id: "answer-en-1",
  query_id: "query-1",
  text: "BSc Computer Science tuition is 1000 USD per semester.",
  citations: [CITATION],
  images: [IMAGE_REF],
  abstained: false,
  confidence: 0.91,
  language: "en",
  next_step: null,
  abstention_reason: null,
};

export const URDU_ANSWER: Answer = {
  answer_id: "answer-ur-1",
  query_id: "query-2",
  text: "بی ایس سی کمپیوٹر سائنس کی فیس 1000 ڈالر ہے۔",
  citations: [URDU_CITATION],
  images: [],
  abstained: false,
  confidence: 0.88,
  language: "ur",
  next_step: null,
  abstention_reason: null,
};

export const ROMAN_URDU_ANSWER: Answer = {
  answer_id: "answer-roman-1",
  query_id: "query-3",
  text: "CS ki fee 1000 dollar hai.",
  citations: [],
  images: [],
  abstained: false,
  confidence: 0.8,
  language: "roman_urdu",
  next_step: null,
  abstention_reason: null,
};

export const ABSTAINING_ANSWER: Answer = {
  answer_id: "answer-abstain-1",
  query_id: "query-4",
  text: "There is not enough evidence to answer that. Next step: search the past-paper archive or ask a more specific question about a course code.",
  citations: [],
  images: [],
  abstained: true,
  confidence: 0,
  language: "en",
  next_step: "Search the past-paper archive for a course code.",
  abstention_reason: "The retrieved chunks do not state the fee.",
};

export const IMAGE_ANSWER: Answer = {
  answer_id: "answer-image-1",
  query_id: "query-5",
  text: "The relevant past-paper page is shown below.",
  citations: [
    {
      chunk_id: "chunk-past-1",
      doc_id: "doc-past",
      source_url: IMAGE_REF.source_url,
      snippet: "Question 4 from the 2024 final.",
      page: 2,
      score: 0.84,
      last_crawled: "2026-11-19T08:00:00Z",
    },
  ],
  images: [IMAGE_REF],
  abstained: false,
  confidence: 0.84,
  language: "en",
  next_step: null,
  abstention_reason: null,
};

/** Real API-local envelopes: `token` frames, then one final `citations` frame. */
export const STREAM_EVENTS: ReadonlyArray<{ event: string; payload: unknown }> = [
  { event: "token", payload: { token: "BSc Computer Science " } },
  { event: "token", payload: { token: "tuition is 1000 USD " } },
  { event: "token", payload: { token: "per semester." } },
  { event: "citations", payload: { answer: ENGLISH_ANSWER } },
];

export const PAPER_RESULTS: PaperRecord[] = [
  {
    question_id: "question-4",
    doc_id: "doc-past",
    source_url: IMAGE_REF.source_url,
    page: 2,
    question_number: 4,
    text: "What is the time complexity of binary search?",
    year: 2024,
    subject: "Computer Science",
    options: ["O(1)", "O(log n)", "O(n)"],
    image_ref: IMAGE_REF,
    course_code: "CS",
    term: "fall",
    exam_type: "final",
    department: "Computer Science",
    last_crawled: PAPER_LAST_CRAWLED,
  },
  {
    question_id: "question-7",
    doc_id: "doc-past-2",
    source_url: "https://uni.example/archive/cs-2023-midterm.pdf",
    page: 1,
    question_number: 7,
    text: "Define a binary search tree.",
    year: 2023,
    subject: "Computer Science",
    options: [],
    image_ref: null,
    course_code: "CS",
    term: "spring",
    exam_type: "midterm",
    department: null,
    last_crawled: PAPER_LAST_CRAWLED,
  },
  {
    question_id: "question-ur-1",
    doc_id: "doc-ur-past",
    source_url: "https://uni.example/archive/cs-2024-urdu.pdf",
    page: 1,
    question_number: 2,
    text: "بائنری سرچ کی Time Complexity کیا ہے؟",
    year: 2024,
    subject: "کمپیوٹر سائنس",
    options: [],
    image_ref: null,
    course_code: "CS",
    term: "fall",
    exam_type: "final",
    department: "کمپیوٹر سائنس",
    last_crawled: PAPER_LAST_CRAWLED,
  },
];

export const EMPTY_PAPER_RESULTS = { results: [] };

export const ERROR_BODY = {
  code: "upstream_unavailable",
  message: "The knowledge service is temporarily unavailable.",
  details: {},
};

export const FEEDBACK_VALIDATION_ERROR = {
  code: "validation_error",
  message: "Feedback payload failed validation.",
  details: {},
};

export const PAPER_VALIDATION_ERROR = {
  code: "validation_error",
  message: "Paper filters failed validation.",
  details: {},
};

export const FEEDBACK_REQUEST = {
  answer_id: "answer-en-1",
  sentiment: "negative" as const,
  reason: "too vague",
};

/** ADR 0009: the 202 response echoes the validated request. */
export const FEEDBACK_RESPONSE: FeedbackResponse = { ...FEEDBACK_REQUEST };
