/**
 * Deterministic mock payload corpus — written before any component (L12).
 * Shapes mirror the frozen core schemas; no fixture invents a provenance value
 * that the payload does not itself carry (L5).
 */

import type { Answer, Citation, ImageRef, PastPaperQuestion } from "../schemas";

export const IMAGE_REF: ImageRef = {
  ref_id: "past-2024-cs-p2",
  source_url: "https://uni.example/archive/cs-2024-final.pdf",
  page: 2,
  caption: "Past paper page 2",
  mime_type: "image/png",
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

export const ENGLISH_ANSWER: Answer = {
  answer_id: "answer-en-1",
  query_id: "query-1",
  text: "BSc Computer Science tuition is 1000 USD per semester.",
  citations: [CITATION],
  images: [IMAGE_REF],
  abstained: false,
  confidence: 0.91,
  language: "en",
};

export const URDU_ANSWER: Answer = {
  answer_id: "answer-ur-1",
  query_id: "query-2",
  text: "بی ایس سی کمپیوٹر سائنس کی فیس 1000 ڈالر ہے۔",
  citations: [
    {
      chunk_id: "chunk-fee-ur-1",
      doc_id: "doc-fee-ur",
      source_url: "https://uni.example/admissions/fees/ur",
      snippet: "کمپیوٹر سائنس کی فیس 1000 ڈالر ہے۔",
      page: null,
      score: null,
    },
  ],
  images: [],
  abstained: false,
  confidence: 0.88,
  language: "ur",
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
    },
  ],
  images: [IMAGE_REF],
  abstained: false,
  confidence: 0.84,
  language: "en",
};

/** SSE frames in arrival order. Tokens precede provenance; the final answer commits. */
export const STREAM_EVENTS: ReadonlyArray<{ event: string; payload: unknown }> = [
  { event: "token", payload: { type: "token", text: "BSc Computer Science " } },
  { event: "token", payload: { type: "token", text: "tuition is 1000 USD " } },
  { event: "token", payload: { type: "token", text: "per semester." } },
  { event: "citation", payload: { type: "citation", citation: CITATION } },
  {
    event: "image",
    payload: { type: "image", image: IMAGE_REF },
  },
  { event: "answer", payload: { type: "answer", answer: ENGLISH_ANSWER } },
];

export const PAPER_RESULTS: PastPaperQuestion[] = [
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
  },
];

export const EMPTY_PAPER_RESULTS = { results: [] };

export const ERROR_BODY = {
  code: "upstream_unavailable",
  message: "The knowledge service is temporarily unavailable.",
};
