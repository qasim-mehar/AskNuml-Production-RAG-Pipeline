"use client";

import { useCallback, useState } from "react";

import { papers as fetchPapers } from "@/lib/api/client";
import { ApiError, logClientError } from "@/lib/api/errors";
import { EMPTY_FILTERS, type FilterKey, type PaperFilters } from "@/lib/filters";
import type { PaperRecord } from "@/lib/api/schemas";

export type PapersStatus = "idle" | "loading" | "error";

/** Finder filter state and lookup composition. No fetching in components. */
export function usePapers() {
  const [filters, setFilters] = useState<PaperFilters>(EMPTY_FILTERS);
  const [results, setResults] = useState<PaperRecord[] | null>(null);
  const [status, setStatus] = useState<PapersStatus>("idle");
  const [error, setError] = useState<ApiError | null>(null);

  const setFilter = useCallback((key: FilterKey, value: string) => {
    setFilters((previous) => ({ ...previous, [key]: value }));
  }, []);

  const search = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const response = await fetchPapers(filters);
      setResults(response.results);
      setStatus("idle");
    } catch (cause) {
      const apiError =
        cause instanceof ApiError
          ? cause
          : new ApiError(String(cause), "schema", 0, null, "unexpected_client_error");
      logClientError(apiError, "papers.search");
      setResults(null);
      setError(apiError);
      setStatus("error");
    }
  }, [filters]);

  return { filters, results, status, error, setFilter, search };
}
