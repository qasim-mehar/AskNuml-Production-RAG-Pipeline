"use client";

import { FilterBar } from "@/components/FilterBar";
import { PageImage } from "@/components/PageImage";
import { detectLanguage, directionFor, langTagFor } from "@/lib/format/language";

import { usePapers } from "./usePapers";

/** Past-paper finder composition with explicit empty and error states. */
export function PapersPage() {
  const { filters, results, status, error, setFilter, search } = usePapers();

  return (
    <main>
      <h1>Past-paper finder</h1>
      <p>Filter by course code, year, term, exam type and department.</p>

      <FilterBar
        filters={filters}
        onChange={setFilter}
        onSubmit={() => {
          void search();
        }}
        disabled={status === "loading"}
      />

      {status === "loading" ? <p role="status">Searching…</p> : null}
      {error ? (
        <div role="alert" className="error">
          {error.message}
          {error.requestId ? <> (request id: {error.requestId})</> : null}
        </div>
      ) : null}

      {results !== null && results.length === 0 && status !== "loading" ? (
        <p role="status">No past papers match these filters.</p>
      ) : null}

      {results !== null && results.length > 0 ? (
        <ul aria-label="Past-paper results">
          {results.map((paper) => (
            <li key={paper.question_id}>
              <h2>
                Question {paper.question_number}
                {paper.year !== null ? ` (${paper.year})` : ""}
              </h2>
              <p
                dir={directionFor(detectLanguage(paper.text))}
                lang={langTagFor(detectLanguage(paper.text))}
              >
                {paper.text}
              </p>
              {paper.subject ? (
                <p
                  dir={directionFor(detectLanguage(paper.subject))}
                  lang={langTagFor(detectLanguage(paper.subject))}
                >
                  Subject: {paper.subject}
                </p>
              ) : null}
              <a href={paper.source_url} target="_blank" rel="noopener noreferrer">
                Source PDF
              </a>
              {paper.image_ref ? <PageImage image={paper.image_ref} /> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </main>
  );
}
