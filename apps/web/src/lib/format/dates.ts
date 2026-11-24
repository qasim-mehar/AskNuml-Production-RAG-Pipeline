/** Pure, deterministic date formatting for provenance fields (L5). */

const FORMATTER = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

/**
 * Format a last-crawled timestamp verbatim in UTC. If the payload value is not
 * a parseable date we show it unchanged — the UI never invents a date (L5).
 */
export function formatLastUpdated(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return FORMATTER.format(date);
}
