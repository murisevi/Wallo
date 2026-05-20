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
  const totalBalance = parseFloat(summary.total_balance);
  const reserved = parseFloat(summary.reserved_for_goals);
  const available = parseFloat(summary.available_to_reserve);
  const globalPct = target > 0 ? (saved / target) * 100 : 0;

  return (
    <div className="rounded-2xl bg-white p-5 shadow-card">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-[#5d605f]">
            Total reservado
          </p>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-[#303333]">{fmt.format(saved)}</span>
            <span className="text-sm text-[#9ca3af]">de {fmt.format(target)}</span>
          </div>
          <div className="mt-3">
            <GoalProgressBar percentage={globalPct} height="h-2.5" />
          </div>
          <div className="mt-4 grid gap-3 border-t border-[#edf0ef] pt-4 text-sm sm:grid-cols-3">
            <div>
              <p className="text-xs text-[#9ca3af]">Saldo conectado</p>
              <p className="font-semibold text-[#303333]">{fmt.format(totalBalance)}</p>
            </div>
            <div>
              <p className="text-xs text-[#9ca3af]">Reservado</p>
              <p className="font-semibold text-[#0060ad]">{fmt.format(reserved)}</p>
            </div>
            <div>
              <p className="text-xs text-[#9ca3af]">Disponible</p>
              <p className="font-semibold text-[#216c36]">{fmt.format(available)}</p>
            </div>
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
