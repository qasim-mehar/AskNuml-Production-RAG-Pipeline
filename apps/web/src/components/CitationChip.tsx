import type { Citation } from "@/lib/api/schemas";
import {
  detectLanguage,
  directionFor,
  langTagFor,
  runLangTagFor,
  splitDirectionRuns,
} from "@/lib/format/language";
import { formatLastUpdated } from "@/lib/format/dates";

type CitationChipProps = {
  citation: Citation;
};

/** Presentational provenance chip. Renders only fields present in the payload (L5). */
export function CitationChip({ citation }: CitationChipProps) {
  const snippetLanguage = detectLanguage(citation.snippet);
  return (
    <li
      className="citation-chip"
      data-chunk-id={citation.chunk_id}
      data-doc-id={citation.doc_id}
      data-score={citation.score ?? undefined}
    >
      <a
        href={citation.source_url}
        target="_blank"
        rel="noopener noreferrer"
        dir={directionFor(snippetLanguage)}
        lang={langTagFor(snippetLanguage)}
      >
        {splitDirectionRuns(citation.snippet).map((run, index) => (
          <span key={index} dir={run.direction} lang={runLangTagFor(snippetLanguage, run.direction)}>
            {run.text}
          </span>
        ))}
      </a>
      <span className="citation-source">{citation.source_url}</span>
      {citation.last_crawled ? (
        <span className="citation-updated">Updated {formatLastUpdated(citation.last_crawled)}</span>
      ) : null}
      {citation.page !== null && citation.page !== undefined ? (
        <span className="citation-page">Page {citation.page}</span>
      ) : null}
    </li>
  );
}
