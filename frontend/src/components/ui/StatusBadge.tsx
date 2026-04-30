interface StatusBadgeProps {
  status: string;
}

const toneMap: Record<string, string> = {
  Draft: 'warning',
  Generated: 'info',
  Uploaded: 'info',
  Validated: 'info',
  Mapped: 'success',
  'Pending BU CDO': 'warning',
  'Pending Central CDO': 'warning',
  'Pending approval': 'warning',
  Approved: 'success',
  Implemented: 'success',
  Live: 'success',
  Active: 'success',
  DRAFT: 'warning',
  ACTIVE: 'success',
  RETIRED: 'neutral',
  Blocked: 'error',
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const tone = toneMap[status] ?? 'neutral';
  return <span className={`chip chip-${tone}`}>{status}</span>;
}