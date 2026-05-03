import { GoalProgressBar } from './GoalProgressBar';
import type { GoalSummary } from '@/types/goals';

const fmt = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' });

interface GoalSummaryCardProps {
  summary: GoalSummary;
  completedExpanded: boolean;
  onToggleCompleted: () => void;
}

export function GoalSummaryCard({
  summary,
  completedExpanded,
  onToggleCompleted,
}: GoalSummaryCardProps) {
  const saved = parseFloat(summary.total_saved);
  const target = parseFloat(summary.total_target);
  const globalPct = target > 0 ? (saved / target) * 100 : 0;

  return (
    <div className="rounded-2xl bg-white p-5 shadow-card">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-[#5d605f]">
            Total ahorrado
          </p>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-[#303333]">{fmt.format(saved)}</span>
            <span className="text-sm text-[#9ca3af]">de {fmt.format(target)}</span>
          </div>
          <div className="mt-3">
            <GoalProgressBar percentage={globalPct} height="h-2.5" />
          </div>
        </div>
        <div className="flex gap-4 text-center sm:flex-col sm:items-end">
          <div>
            <p className="text-xl font-bold text-[#0060ad]">{summary.active_count}</p>
            <p className="text-xs text-[#5d605f]">activos</p>
          </div>
          {summary.completed_count > 0 && (
            <button onClick={onToggleCompleted} className="text-right hover:underline">
              <p className="text-xl font-bold text-green-600">{summary.completed_count}</p>
              <p className="text-xs text-[#5d605f]">
                completados {completedExpanded ? '▲' : '▼'}
              </p>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
