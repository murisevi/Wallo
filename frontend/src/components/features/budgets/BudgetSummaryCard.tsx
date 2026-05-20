'use client';

import { BudgetDonutChart } from './BudgetDonutChart';
import type { BudgetSummary } from '@/types/budget';

function formatEur(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
  }).format(num);
}

function statusBadgeClass(status: string): string {
  if (status === 'SUPERADO') return 'bg-red-100 text-red-700';
  if (status === 'CERCA DEL LÍMITE') return 'bg-yellow-100 text-yellow-700';
  return 'bg-green-100 text-green-700';
}

interface BudgetSummaryCardProps {
  data: BudgetSummary;
}

export function BudgetSummaryCard({ data }: BudgetSummaryCardProps) {
  const availableNum = parseFloat(data.total_available);
  const isOverBudget = availableNum < 0;

  return (
    <div className="rounded-2xl bg-gray-50 p-5 shadow-card">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-stretch">

        {/* Left: gasto total + barra + donut */}
        <div className="flex flex-1 flex-col gap-3 sm:flex-row sm:items-center">
          {/* Donut chart */}
          <BudgetDonutChart budgets={data.budgets} totalSpent={data.total_spent} />

          {/* Texto */}
          <div className="flex-1 space-y-3">
            <div>
              <p className="text-xs font-semibold text-[#5d605f]">Gasto Total</p>
              <div className="mt-0.5 flex items-center gap-3">
                <span className="text-3xl font-extrabold tracking-tight text-[#303333]">
                  {formatEur(data.total_spent)}
                </span>
                <span
                  className={`rounded-full px-3 py-0.5 text-xs font-bold ${statusBadgeClass(data.status)}`}
                >
                  {data.status}
                </span>
              </div>
            </div>

            {parseFloat(data.total_limit) > 0 && (
              <div>
                <div className="mb-1 flex items-center justify-between text-xs text-[#5d605f]">
                  <span>Progreso mensual</span>
                  <span className="font-semibold">
                    {data.percentage.toFixed(0)}% de {formatEur(data.total_limit)}
                  </span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-gray-200">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[#0060ad] to-[#68abff] transition-all"
                    style={{ width: `${Math.min(data.percentage, 100)}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: disponible + mensaje */}
        <div className="shrink-0 rounded-xl border border-[#e8e9e8] bg-white p-4 sm:w-64">
          <p className="text-xs font-semibold text-[#5d605f]">Disponible</p>
          <p className={`mt-0.5 text-2xl font-extrabold ${isOverBudget ? 'text-red-600' : 'text-green-600'}`}>
            {isOverBudget ? '' : '+'}{formatEur(data.total_available)}
          </p>
          <p className="mt-2 text-xs leading-relaxed text-[#5d605f]">
            {data.comparison_message}
          </p>
        </div>
      </div>
    </div>
  );
}
