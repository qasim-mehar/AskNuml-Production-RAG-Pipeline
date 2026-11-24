import type { Language } from "@/lib/api/schemas";
import {
  directionFor,
  langTagFor,
  runLangTagFor,
  splitDirectionRuns,
} from "@/lib/format/language";

type MessageBubbleProps = {
  text: string;
  language: Language;
  role?: "user" | "assistant";
};

/** Direction-aware message. Each mixed-script run keeps its own direction (L7). */
export function MessageBubble({ text, language, role = "assistant" }: MessageBubbleProps) {
  return (
    <article
      className="message-bubble"
      data-role={role}
      dir={directionFor(language)}
      lang={langTagFor(language)}
    >
      {splitDirectionRuns(text).map((run, index) => (
        <span
          key={index}
          dir={run.direction}
          lang={runLangTagFor(language, run.direction)}
        >
          {run.text}
        </span>
      ))}
    </article>
  );
}
