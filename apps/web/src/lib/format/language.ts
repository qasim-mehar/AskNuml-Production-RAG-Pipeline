/** Pure language/direction helpers for multilingual, mixed-direction text (L7). */

import type { Language } from "../api/schemas";

export type Direction = "ltr" | "rtl";

export type DirectionRun = { text: string; direction: Direction };

const URDU_SCRIPT =
  /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/u;

/** Roman Urdu uses Latin script, so its direction is left-to-right. */
export function directionFor(language: Language): Direction {
  return language === "ur" ? "rtl" : "ltr";
}

/** BCP 47 tag for a language value, including Roman Urdu's Latin script tag. */
export function langTagFor(language: Language): string {
  if (language === "ur") return "ur";
  if (language === "roman_urdu") return "ur-Latn";
  return "en";
}

/** Language tag for one direction run inside a message (L7). */
export function runLangTagFor(language: Language, direction: Direction): string {
  if (direction === "rtl") return "ur";
  return language === "roman_urdu" ? "ur-Latn" : "en";
}

/** Best-effort detection for the composer's automatic language choice (L7). */
export function detectLanguage(text: string): Language {
  if (URDU_SCRIPT.test(text)) return "ur";
  const tokens = new Set(text.toLowerCase().match(/[a-z]+/gu) ?? []);
  const romanUrduMarkers = [
    "kya",
    "hai",
    "kaise",
    "karna",
    "mein",
    "aur",
    "nahi",
    "nahin",
    "ko",
    "ki",
    "ka",
    "khan",
  ];
  if (romanUrduMarkers.some((marker) => tokens.has(marker))) return "roman_urdu";
  return "en";
}

/**
 * Split mixed English/Urdu text into runs so each keeps its own direction.
 * Whitespace, digits and punctuation are neutral and stay with the surrounding
 * run; only Latin and Urdu-script characters start a new run.
 */
export function splitDirectionRuns(text: string): DirectionRun[] {
  const runs: DirectionRun[] = [];
  let current = "";
  let currentDirection: Direction = "ltr";
  let started = false;

  for (const character of text) {
    const script: Direction | null = URDU_SCRIPT.test(character)
      ? "rtl"
      : /[A-Za-z]/u.test(character)
        ? "ltr"
        : null;
    if (script !== null && script !== currentDirection && started) {
      runs.push({ text: current, direction: currentDirection });
      current = "";
    }
    if (script !== null) currentDirection = script;
    current += character;
    started = true;
  }
  if (started) runs.push({ text: current, direction: currentDirection });
  return runs;
}
