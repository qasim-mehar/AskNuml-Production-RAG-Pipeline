import { formatLastUpdated } from "@/lib/format/dates";
import type { Citation } from "@/lib/api/schemas";

type CitationChipProps = {
  citation: Citation;
};

/** Presentational provenance chip. Renders only fields present in the payload (L5). */
export function CitationChip({ citation }: CitationChipProps) {
  return (
    <li
      className="citation-chip"
      data-chunk-id={citation.chunk_id}
      data-doc-id={citation.doc_id}
      data-score={citation.score ?? undefined}
    >
      <a href={citation.source_url} target="_blank" rel="noopener noreferrer">
        {citation.snippet}
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
