/** Typed client-side errors and structured logging (L10). No React, no fetching. */

/** Header Lane G must return so Web can correlate an error with a server trace. */
export const REQUEST_ID_HEADER = "x-request-id";

export type ApiErrorKind = "http" | "schema" | "stream";

/** Every client failure carries its kind, HTTP status and the API trace id when present. */
export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number;
  readonly requestId: string | null;
  readonly code: string | null;

  constructor(
    message: string,
    kind: ApiErrorKind,
    status: number,
    requestId: string | null,
    code: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.requestId = requestId;
    this.code = code;
  }
}

/** Prefer the API trace header; fall back to common tracing headers. */
export function requestIdFrom(headers: Headers): string | null {
  return (
    headers.get(REQUEST_ID_HEADER) ??
    headers.get("x-trace-id") ??
    headers.get("traceparent") ??
    null
  );
}

/** Build a typed HTTP error, reading an optional {code, message} JSON body. */
export async function httpErrorFrom(response: Response, path: string): Promise<ApiError> {
  const requestId = requestIdFrom(response.headers);
  let code: string | null = null;
  let message = `Request to ${path} failed with status ${response.status}`;

  const body: unknown = await response.json().catch(() => null);
  if (typeof body === "object" && body !== null) {
    const record = body as Record<string, unknown>;
    if (typeof record["code"] === "string") code = record["code"];
    if (typeof record["message"] === "string") message = record["message"];
  }

  return new ApiError(message, "http", response.status, requestId, code);
}

/** Structured JSON log line — never a bare print, never a swallowed failure. */
export function logClientError(error: ApiError, context: string): void {
  console.error(
    JSON.stringify({
      level: "error",
      event: "web_api_error",
      context,
      kind: error.kind,
      status: error.status,
      request_id: error.requestId,
      code: error.code,
      message: error.message,
    }),
  );
}
