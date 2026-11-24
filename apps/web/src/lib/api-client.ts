/**
 * Minimal typed JSON fetch helper.
 * Pure TypeScript: uses global fetch, no React or application state.
 */

import { httpErrorFrom } from "./api/errors";

const DEFAULT_TIMEOUT_MS = 10_000;

/** Fetch a path and parse its JSON body as T, aborting after a timeout. */
export async function fetchJson<T>(path: string): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  try {
    const response = await fetch(path, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw await httpErrorFrom(response, path);
    }

    return (await response.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}
