/**
 * Canonical API routes. The artifact-backed routes (query, stream) are checked
 * against `mocks/openapi-emitted.json` in tests, so they cannot drift from
 * `apps/api/openapi.json`. The rest come from binding ADRs; the artifact still
 * lacks those routes (see CONTRACTS.md CONTRACT-CHANGE notes).
 */
export const ROUTES = {
  query: "/api/v1/query",
  stream: "/api/v1/query/stream",
  feedback: "/api/v1/feedback",
  papers: "/api/papers",
  imagesPrefix: "/api/images/",
} as const;

/** Build the image fallback route from the object-store ref id (ADR 0007). */
export function imageRouteFor(refId: string): string {
  return `${ROUTES.imagesPrefix}${encodeURIComponent(refId)}`;
}
