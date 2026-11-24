import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CITATION } from "@/lib/api/mocks/fixtures";

import { CitationChip } from "./CitationChip";

describe("CitationChip", () => {
  it("renders exactly the provenance fields the payload carries", () => {
    render(
      <ul>
        <CitationChip citation={CITATION} />
      </ul>,
    );
    expect(screen.getByRole("link")).toHaveAttribute("href", CITATION.source_url);
    expect(screen.getByText(CITATION.source_url)).toBeInTheDocument();
    expect(screen.getByText(CITATION.snippet)).toBeInTheDocument();
    expect(screen.getByText("Updated 20 Nov 2026")).toBeInTheDocument();
    expect(screen.getByText("Page 3")).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("does not invent an updated date or page when the payload omits them", () => {
    render(
      <ul>
        <CitationChip
          citation={{
            chunk_id: "chunk-x",
            doc_id: "doc-x",
            source_url: "https://uni.example/x",
            snippet: "Snippet",
            page: null,
            score: null,
          }}
        />
      </ul>,
    );
    expect(screen.queryByText(/Updated/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Page/)).not.toBeInTheDocument();
  });
});
