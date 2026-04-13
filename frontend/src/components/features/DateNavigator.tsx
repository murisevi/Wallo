'use client';

import { ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react';
import type { ViewPeriod } from '@/types/reports';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const MONTHS_ES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

/** Number of 7-day week blocks in a given month (4 or 5). */
function weeksInMonth(year: number, month: number): number {
  // JS Date: month is 0-indexed; day 0 = last day of previous month trick
  const lastDay = new Date(year, month, 0).getDate();
  return Math.floor((lastDay - 1) / 7) + 1;
}

function periodLabel(refDate: Date, period: ViewPeriod): string {
  const y = refDate.getFullYear();
  if (period === 'year') return String(y);
  if (period === 'quarter') {
    const q = Math.floor(refDate.getMonth() / 3) + 1;
    return `T${q} · ${y}`;
  }
  // month
  return `${MONTHS_ES[refDate.getMonth()]} ${y}`;
}

/** True when refDate is already at the current period (no future navigation). */
function isAtCurrentOrFuture(refDate: Date, period: ViewPeriod): boolean {
  const now = new Date();
  const ry = refDate.getFullYear();
  const ny = now.getFullYear();
  if (period === 'year') return ry >= ny;
  if (period === 'quarter') {
    const rq = Math.floor(refDate.getMonth() / 3);
    const nq = Math.floor(now.getMonth() / 3);
    return ry > ny || (ry === ny && rq >= nq);
  }
  // month
  return ry > ny || (ry === ny && refDate.getMonth() >= now.getMonth());
}

/** True when refDate is already at the same period as today. */
function isToday(refDate: Date, period: ViewPeriod): boolean {
  const now = new Date();
  if (period === 'year') return refDate.getFullYear() === now.getFullYear();
  if (period === 'quarter') {
    return (
      refDate.getFullYear() === now.getFullYear() &&
      Math.floor(refDate.getMonth() / 3) === Math.floor(now.getMonth() / 3)
    );
  }
  return (
    refDate.getFullYear() === now.getFullYear() &&
    refDate.getMonth() === now.getMonth()
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface DateNavigatorProps {
  period: ViewPeriod;
  refDate: Date;
  /** 1-indexed selected week within the month. null = full month. */
  weekFilter: number | null;
  onPrev: () => void;
  onNext: () => void;
  onReset: () => void;
  onWeekSelect: (week: number | null) => void;
}

export default function DateNavigator({
  period,
  refDate,
  weekFilter,
  onPrev,
  onNext,
  onReset,
  onWeekSelect,
}: DateNavigatorProps) {
  const label = periodLabel(refDate, period);
  const canNext = !isAtCurrentOrFuture(refDate, period);
  const atToday = isToday(refDate, period) && weekFilter === null;

  const numWeeks =
    period === 'month'
      ? weeksInMonth(refDate.getFullYear(), refDate.getMonth() + 1)
      : 0;

  return (
    <div className="flex flex-col items-center gap-3">
      {/* ── Arrow navigator row ─────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        {/* Prev arrow */}
        <button
          onClick={onPrev}
          title="Período anterior"
          className="flex h-8 w-8 items-center justify-center rounded-full text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-900"
        >
          <ChevronLeft size={18} />
        </button>

        {/* Period label */}
        <span className="min-w-[180px] text-center text-sm font-semibold text-gray-900">
          {label}
          {period === 'month' && weekFilter !== null && (
            <span className="ml-1.5 text-xs font-normal text-gray-400">
              · Semana {weekFilter}
            </span>
          )}
        </span>

        {/* Next arrow */}
        <button
          onClick={onNext}
          disabled={!canNext}
          title="Período siguiente"
          className="flex h-8 w-8 items-center justify-center rounded-full text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <ChevronRight size={18} />
        </button>

        {/* Reset to today */}
        {!atToday && (
          <button
            onClick={onReset}
            title="Volver al período actual"
            className="ml-1 flex items-center gap-1 rounded-full border border-gray-200 px-2.5 py-1 text-xs font-medium text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-900"
          >
            <RotateCcw size={11} />
            Hoy
          </button>
        )}
      </div>

      {/* ── Week sub-selector (only for month period) ───────────────── */}
      {period === 'month' && (
        <div className="flex items-center gap-1.5 flex-wrap justify-center">
          <button
            onClick={() => onWeekSelect(null)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-all ${
              weekFilter === null
                ? 'bg-[#1B4F72] text-white shadow-sm'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700'
            }`}
          >
            Todo el mes
          </button>
          {Array.from({ length: numWeeks }, (_, i) => i + 1).map((w) => (
            <button
              key={w}
              onClick={() => onWeekSelect(w)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-all ${
                weekFilter === w
                  ? 'bg-[#1B4F72] text-white shadow-sm'
                  : 'bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700'
              }`}
            >
              Sem {w}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
