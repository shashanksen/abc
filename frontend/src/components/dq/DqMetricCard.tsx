interface DqMetricCardProps {
  label: string;
  value: string;
  meta?: string;
}

export function DqMetricCard({ label, value, meta }: DqMetricCardProps) {
  return (
    <article className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {meta ? <div className="stat-meta">{meta}</div> : null}
    </article>
  );
}