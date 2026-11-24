/** Pure Server-Sent Events framing parser. No React, no fetching. */

export type SseEvent = { event: string; data: string };

/** Decode an SSE byte stream into named events, including a final unterminated block. */
export async function* parseSseStream(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<SseEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let pendingCarriageReturn = false;

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      let text = decoder.decode(value, { stream: true });
      if (pendingCarriageReturn) {
        if (text.startsWith("\n")) {
          buffer += "\n"; // the completed CRLF is still a line break
          text = text.slice(1);
        } else {
          text = `\r${text}`;
        }
      }
      pendingCarriageReturn = text.endsWith("\r");
      if (pendingCarriageReturn) text = text.slice(0, -1);
      buffer += text.replaceAll("\r\n", "\n");

      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const event = parseEventBlock(block);
        if (event) yield event;
        boundary = buffer.indexOf("\n\n");
      }
    }
  } finally {
    reader.releaseLock();
  }

  const tail = parseEventBlock(buffer.trim());
  if (tail) yield tail;
}

/** Parse one SSE block: `event:` names the type, `data:` lines carry the payload. */
export function parseEventBlock(block: string): SseEvent | null {
  let event = "message";
  const data: string[] = [];

  for (const line of block.split("\n")) {
    if (line.startsWith(":")) continue; // keep-alive comment
    const separator = line.indexOf(":");
    const field = separator === -1 ? line : line.slice(0, separator);
    let value = separator === -1 ? "" : line.slice(separator + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") event = value;
    if (field === "data") data.push(value);
  }

  return data.length === 0 ? null : { event, data: data.join("\n") };
}

/** Build an SSE block from a named event and a JSON payload (used by mocks). */
export function formatSseEvent(event: string, payload: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(payload)}\n\n`;
}
