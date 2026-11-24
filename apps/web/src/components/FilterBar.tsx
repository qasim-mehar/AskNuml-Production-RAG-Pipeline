import {
  EXAM_TYPE_OPTIONS,
  type FilterKey,
  type PaperFilters,
  TERM_OPTIONS,
} from "@/lib/filters";

type FilterBarProps = {
  filters: PaperFilters;
  onChange: (key: FilterKey, value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
};

/** Presentational finder controls. No fetching; state lives in the feature hook. */
export function FilterBar({ filters, onChange, onSubmit, disabled = false }: FilterBarProps) {
  return (
    <form
      className="filter-bar"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div>
        <label htmlFor="filter-course">Course code</label>
        <input
          id="filter-course"
          type="text"
          value={filters.courseCode}
          disabled={disabled}
          onChange={(event) => onChange("courseCode", event.target.value)}
        />
      </div>
      <div>
        <label htmlFor="filter-year">Year</label>
        <input
          id="filter-year"
          type="number"
          min="1900"
          max="2100"
          value={filters.year}
          disabled={disabled}
          onChange={(event) => onChange("year", event.target.value)}
        />
      </div>
      <div>
        <label htmlFor="filter-term">Term</label>
        <select
          id="filter-term"
          value={filters.term}
          disabled={disabled}
          onChange={(event) => onChange("term", event.target.value)}
        >
          {TERM_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="filter-exam">Exam type</label>
        <select
          id="filter-exam"
          value={filters.examType}
          disabled={disabled}
          onChange={(event) => onChange("examType", event.target.value)}
        >
          {EXAM_TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="filter-department">Department</label>
        <input
          id="filter-department"
          type="text"
          value={filters.department}
          disabled={disabled}
          onChange={(event) => onChange("department", event.target.value)}
        />
      </div>
      <button type="submit" disabled={disabled}>
        Find past papers
      </button>
    </form>
  );
}
