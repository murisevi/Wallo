'use client';

import type { Budget } from '@/types/budget';

const DONUT_COLORS: Record<string, string> = {
  'shopping-cart': '#16a34a',
  utensils:        '#d97706',
  car:             '#ef4444',
  home:            '#2563eb',
  heart:           '#ec4899',
  shirt:           '#9333ea',
  book:            '#4f46e5',
  repeat:          '#7c3aed',
};
const DEFAULT_COLOR = '#94a3b8';

function formatEur(value: number): string {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
  }).format(value);
}

interface BudgetDonutChartProps {
  budgets: Budget[];
  totalSpent: string;
}

export function BudgetDonutChart({ budgets, totalSpent }: BudgetDonutChartProps) {
  const chartData = budgets
    .filter((b) => parseFloat(b.amount_spent) > 0)
    .map((b) => ({
      name: b.category_name,
      value: parseFloat(b.amount_spent),
      color: DONUT_COLORS[b.category_icon] ?? DEFAULT_COLOR,
    }));

  if (chartData.length < 2) return null;

  const total = chartData.reduce((acc, d) => acc + d.value, 0);

  const SIZE = 180;
  const STROKE = 28;
  const r = (SIZE - STROKE) / 2;
  const cx = SIZE / 2;
  const cy = SIZE / 2;
  const circumference = 2 * Math.PI * r;

  // Build dash segments: each circle overlays the full track with its own
  // dasharray+dashoffset so only its arc is visible.
  let cumulativeArc = 0;
  const segments = chartData.map((d) => {
    const arc = (d.value / total) * circumference;
    const dashOffset = circumference - cumulativeArc;
    cumulativeArc += arc;
    return { ...d, arc, dashOffset };
  });

  return (
    <div className="relative flex items-center justify-center" style={{ width: SIZE, height: SIZE }}>
      <svg
        width={SIZE}
        height={SIZE}
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        style={{ transform: 'rotate(-90deg)' }}
        aria-hidden="true"
      >
        {/* Background track */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#f1f5f9"
          strokeWidth={STROKE}
        />
        {/* Coloured segments */}
        {segments.map((seg) => (
          <circle
            key={seg.name}
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke={seg.color}
            strokeWidth={STROKE}
            strokeDasharray={`${seg.arc} ${circumference}`}
            strokeDashoffset={seg.dashOffset}
          />
        ))}
      </svg>

      {/* Center label — rotated back to normal */}
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="text-[9px] font-bold uppercase tracking-widest text-[#5d605f]">
          Total
        </span>
        <span className="text-sm font-extrabold text-[#303333]">
          {formatEur(parseFloat(totalSpent))}
        </span>
      </div>
    </div>
  );
}
