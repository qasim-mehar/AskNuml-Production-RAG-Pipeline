/**
 * Deterministic fake backend for local Lighthouse runs only (L1: labelled mode).
 * Serves the generated contract fixtures — no live API, no LLM, no network egress.
 * Start with: node apps/web/scripts/fake-backend.mjs
 */

import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const mockDir = join(here, "..", "src", "lib", "api", "mocks");
const contract = JSON.parse(await readFile(join(mockDir, "openapi-emitted.json"), "utf8"));
const core = JSON.parse(await readFile(join(mockDir, "core-emitted.json"), "utf8"));

const PORT = Number(process.env.FAKE_BACKEND_PORT ?? 8787);
const PIXEL = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);

function sendJson(response, status, body, requestId = "req-fake-001") {
  response.writeHead(status, {
    "content-type": "application/json",
    "x-request-id": requestId,
    "access-control-allow-origin": "*",
  });
  response.end(JSON.stringify(body));
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${PORT}`);
  const path = url.pathname;

  if (path === contract.routes.query && request.method === "POST") {
    sendJson(response, 200, core.answer, "req-fake-query-200");
    return;
  }
  if (path === contract.routes.stream && request.method === "POST") {
    response.writeHead(200, {
      "content-type": "text/event-stream",
      "cache-control": "no-cache",
      "x-request-id": "req-fake-stream-001",
    });
    const frame = (event, payload) => `event: ${event}\ndata: ${JSON.stringify(payload)}\n\n`;
    response.write(frame("token", { token: "The fee is " }));
    response.write(frame("token", { token: "1000 USD." }));
    response.write(frame("citations", { answer: core.answer }));
    response.end();
    return;
  }
  if (path === contract.conventions.feedback && request.method === "POST") {
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    const body = JSON.parse(Buffer.concat(chunks).toString("utf8"));
    sendJson(response, 202, body, "req-fake-feedback-202");
    return;
  }
  if (path === contract.conventions.papers && request.method === "GET") {
    sendJson(response, 200, { results: [core.past_paper] }, "req-fake-papers-200");
    return;
  }
  if (path.startsWith(contract.conventions.images_prefix) && request.method === "GET") {
    response.writeHead(200, { "content-type": "image/png" });
    response.end(PIXEL);
    return;
  }
  sendJson(
    response,
    404,
    { code: "not_found", message: "No fake backend handler", details: {} },
    "req-fake-404",
  );
});

server.listen(PORT, "127.0.0.1", () => {
  process.stdout.write(`${JSON.stringify({ event: "fake_backend_ready", port: PORT })}\n`);
});
