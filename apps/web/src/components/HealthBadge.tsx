type HealthBadgeProps = {
  status: string;
};

/** Presentational badge that displays a status string. No fetching or hooks. */
export function HealthBadge({ status }: HealthBadgeProps) {
  return <span role="status">{status}</span>;
}
