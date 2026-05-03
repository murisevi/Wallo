interface GoalProgressBarProps {
  percentage: number;
  height?: string;
}

function barColor(pct: number): string {
  if (pct >= 100) return '#059669';
  if (pct >= 80) return '#10B981';
  if (pct >= 50) return '#6366F1';
  if (pct > 0) return '#3B82F6';
  return '#D1D5DB';
}

export function GoalProgressBar({ percentage, height = 'h-3' }: GoalProgressBarProps) {
  const clamped = Math.min(percentage, 100);
  const color = barColor(percentage);

  return (
    <div className="relative w-full">
      <div className={`relative w-full ${height} overflow-hidden rounded-full bg-[#f3f4f3]`}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${clamped}%`, backgroundColor: color }}
        />
        {/* Milestone markers at 25%, 50%, 75% */}
        {[25, 50, 75].map((mark) => (
          <div
            key={mark}
            className="absolute top-0 h-full w-px bg-white/60"
            style={{ left: `${mark}%` }}
          />
        ))}
      </div>
    </div>
  );
}
