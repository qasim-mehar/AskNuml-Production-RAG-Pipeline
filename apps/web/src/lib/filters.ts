/** Pure finder filter state and query-string encoding (no React, no fetching). */

export type PaperFilters = {
  courseCode: string;
  year: string;
  term: string;
  examType: string;
  department: string;
};

export type FilterKey = keyof PaperFilters;

export const EMPTY_FILTERS: PaperFilters = {
  courseCode: "",
  year: "",
  term: "",
  examType: "",
  department: "",
};

/** Static UI vocabulary — control labels, not facts from the API payload. */
export const TERM_OPTIONS = [
  { value: "", label: "Any term" },
  { value: "fall", label: "Fall" },
  { value: "spring", label: "Spring" },
  { value: "summer", label: "Summer" },
] as const;

export const EXAM_TYPE_OPTIONS = [
  { value: "", label: "Any exam type" },
  { value: "midterm", label: "Midterm" },
  { value: "final", label: "Final" },
  { value: "quiz", label: "Quiz" },
] as const;

/** Encode only non-empty filters; URLSearchParams handles Urdu department names. */
export function filtersToQueryString(filters: PaperFilters): string {
  const params = new URLSearchParams();
  const entries: ReadonlyArray<readonly [string, string]> = [
    ["course_code", filters.courseCode],
    ["year", filters.year],
    ["term", filters.term],
    ["exam_type", filters.examType],
    ["department", filters.department],
  ];
  for (const [key, value] of entries) {
    const trimmed = value.trim();
    if (trimmed !== "") params.set(key, trimmed);
  }
  return params.toString();
}
