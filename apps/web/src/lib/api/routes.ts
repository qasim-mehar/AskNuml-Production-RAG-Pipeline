/**
 * Canonical API routes. Routes resolved from the served artifact's operationIds
 * (query, stream, papers) are checked against `mocks/openapi-emitted.json` in
 * tests, so they cannot drift from `apps/api/openapi.json`. Feedback and the
 * image prefix come from binding ADRs (ADR 0009 / ADR 0007; see CONTRACTS.md).
 */
export const ROUTES = {
  query: "/api/v1/query",
  stream: "/api/v1/query/stream",
  feedback: "/api/v1/feedback",
  papers: "/api/v1/papers",
  imagesPrefix: "/api/images/",
} as const;

/** Build the image fallback route from the object-store ref id (ADR 0007). */
export function imageRouteFor(refId: string): string {
  return `${ROUTES.imagesPrefix}${encodeURIComponent(refId)}`;
}
