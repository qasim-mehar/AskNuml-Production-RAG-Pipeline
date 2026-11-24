import { describe, expect, it } from "vitest";

import { parseEventBlock, parseSseStream, type SseEvent } from "./sse";

function streamFrom(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}

describe("SSE framing", () => {
  it("ignores comments and supports multi-line data", () => {
    expect(parseEventBlock(": keep-alive\nevent: citations\ndata: {\"a\":1}\ndata: {\"b\":2}")).toEqual({
      event: "citations",
      data: '{"a":1}\n{"b":2}',
    });
  });

  it("handles a CRLF boundary split across two reads", async () => {
    const events: SseEvent[] = [];
    for await (const event of parseSseStream(
      streamFrom(["event: token\r", '\ndata: {"token":"hi"}\r\n\r\n']),
    )) {
      events.push(event);
    }
    expect(events).toEqual([{ event: "token", data: '{"token":"hi"}' }]);
  });

  it("emits a final event that has no trailing blank line", async () => {
    const events: SseEvent[] = [];
    for await (const event of parseSseStream(streamFrom(['data: {"done":true}']))) {
      events.push(event);
    }
    expect(events).toEqual([{ event: "message", data: '{"done":true}' }]);
  });
});
