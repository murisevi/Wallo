'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import PeriodSelector from '@/components/features/PeriodSelector';
import DateNavigator from '@/components/features/DateNavigator';
import SpendingDonutChart from '@/components/features/SpendingDonutChart';
import IncomeDonutChart from '@/components/features/IncomeDonutChart';
import IncomeExpensesLineChart from '@/components/features/IncomeExpensesLineChart';
import BalanceEvolutionChart from '@/components/features/BalanceEvolutionChart';
import ExportCSVButton from '@/components/features/ExportCSVButton';
import {
  useBalanceEvolution,
  useCashflowSankey,
  useIncomeByCategory,
  useIncomeVsExpenses,
  useSpendingByCategory,
} from '@/hooks/useReports';
import { useCategories } from '@/hooks/useCategories';
import type { PeriodEnum, ViewPeriod } from '@/types/reports';

// Sankey uses d3 — dynamic import avoids SSR bundle issues
const CashflowSankeyChart = dynamic(
  () => import('@/components/features/CashflowSankeyChart'),
  { ssr: false },
);

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function CardSkeleton({ height = 'h-72' }: { height?: string }) {
  return <div className={`${height} animate-pulse rounded-xl bg-gray-200`} />;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const MONTHS_ES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

function periodLabel(period: ViewPeriod, refDate: Date, weekFilter: number | null): string {
  const monthName = MONTHS_ES[refDate.getMonth()];
  if (period === 'month' && weekFilter !== null) {
    return `Semana ${weekFilter} · ${monthName} ${refDate.getFullYear()}`;
  }
  if (period === 'month') return `${monthName} ${refDate.getFullYear()}`;
  if (period === 'quarter') {
    const q = Math.floor(refDate.getMonth() / 3) + 1;
    return `T${q} ${refDate.getFullYear()}`;
  }
  return `${refDate.getFullYear()}`;
}

function donutSubtitle(period: ViewPeriod, refDate: Date, weekFilter: number | null): string {
  const base = periodLabel(period, refDate, weekFilter);
  return `Distribución del gasto — ${base}`;
}

function incomeSubtitle(period: ViewPeriod, refDate: Date, weekFilter: number | null): string {
  const base = periodLabel(period, refDate, weekFilter);
  return `Distribución de ingresos — ${base}`;
}

function lineSubtitle(period: ViewPeriod, refDate: Date, weekFilter: number | null): string {
  const monthName = MONTHS_ES[refDate.getMonth()];
  if (period === 'month' && weekFilter !== null) {
    return `Semana ${weekFilter} de ${monthName} ${refDate.getFullYear()} — día a día`;
  }
  if (period === 'month') return `${monthName} ${refDate.getFullYear()} — semana a semana`;
  if (period === 'quarter') {
    const q = Math.floor(refDate.getMonth() / 3) + 1;
    return `T${q} ${refDate.getFullYear()} — mes a mes`;
  }
  return `${refDate.getFullYear()} — mes a mes`;
}

/** Mirrors backend _get_date_range — returns ISO date strings for the period. */
function getDateRange(
  period: ViewPeriod,
  refDate: Date,
  weekFilter: number | null,
): { dateFrom: string; dateTo: string } {
  const pad = (n: number) => String(n).padStart(2, '0');
  const y = refDate.getFullYear();
  const m = refDate.getMonth() + 1; // 1-indexed

  if (weekFilter !== null) {
    const lastDay = new Date(y, m, 0).getDate();
    const startDay = (weekFilter - 1) * 7 + 1;
    const endDay = Math.min(startDay + 6, lastDay);
    return { dateFrom: `${y}-${pad(m)}-${pad(startDay)}`, dateTo: `${y}-${pad(m)}-${pad(endDay)}` };
  }
  if (period === 'month') {
    const lastDay = new Date(y, m, 0).getDate();
    return { dateFrom: `${y}-${pad(m)}-01`, dateTo: `${y}-${pad(m)}-${pad(lastDay)}` };
  }
  if (period === 'quarter') {
    const q = Math.floor((m - 1) / 3);
    const sm = q * 3 + 1;
    const em = sm + 2;
    const endLast = new Date(y, em, 0).getDate();
    return { dateFrom: `${y}-${pad(sm)}-01`, dateTo: `${y}-${pad(em)}-${pad(endLast)}` };
  }
  return { dateFrom: `${y}-01-01`, dateTo: `${y}-12-31` };
}

// ---------------------------------------------------------------------------
// Error card
// ---------------------------------------------------------------------------

function ErrorCard({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex h-64 items-center justify-center gap-1 text-sm text-red-500">
      Error al cargar los datos.
      <button className="ml-1 underline" onClick={onRetry}>
        Reintentar
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main client component
// ---------------------------------------------------------------------------

export default function ReportsClient() {
  const today = new Date();
  const router = useRouter();

  // ── User-selectable period (month | quarter | year) ──────────────────────
  const [viewPeriod, setViewPeriod] = useState<ViewPeriod>('quarter');

  // ── Navigation: which concrete date window we're viewing ─────────────────
  const [refDate, setRefDate] = useState<Date>(today);

  // ── Week drill-down: 1-4 (Semana N of the current month), null = full month
  const [weekFilter, setWeekFilter] = useState<number | null>(null);

  // ── Derived API params ────────────────────────────────────────────────────
  const apiPeriod: PeriodEnum = weekFilter !== null ? 'week' : viewPeriod;

  const apiDateStr = useMemo(() => {
    const y = refDate.getFullYear();
    const m = String(refDate.getMonth() + 1).padStart(2, '0');
    if (weekFilter !== null) {
      const d = String((weekFilter - 1) * 7 + 1).padStart(2, '0');
      return `${y}-${m}-${d}`;
    }
    return `${y}-${m}-01`;
  }, [refDate, weekFilter]);

  // ── Queries ───────────────────────────────────────────────────────────────
  const balanceQuery = useBalanceEvolution(apiPeriod, apiDateStr);
  const spendingQuery = useSpendingByCategory(apiPeriod, apiDateStr);
  const incomeQuery = useIncomeByCategory(apiPeriod, apiDateStr);
  const incomeExpensesQuery = useIncomeVsExpenses(apiPeriod, apiDateStr);
  const sankeyQuery = useCashflowSankey(apiPeriod, apiDateStr);
  const { data: allCategories } = useCategories();

  // ── Navigation handlers ───────────────────────────────────────────────────
  function navigate(direction: -1 | 1) {
    setRefDate((prev) => {
      const d = new Date(prev);
      if (viewPeriod === 'month') d.setMonth(d.getMonth() + direction);
      else if (viewPeriod === 'quarter') d.setMonth(d.getMonth() + direction * 3);
      else d.setFullYear(d.getFullYear() + direction);
      return d;
    });
    setWeekFilter(null);
  }

  function handlePeriodChange(p: ViewPeriod) {
    setViewPeriod(p);
    setWeekFilter(null);
  }

  function handleReset() {
    setRefDate(new Date());
    setWeekFilter(null);
  }

  function handleWeekSelect(week: number | null) {
    setWeekFilter(week);
  }

  // ── Category click → navigate to /transactions with filters ─────────────
  function handleCategoryClick(categoryName: string) {
    const { dateFrom, dateTo } = getDateRange(viewPeriod, refDate, weekFilter);
    const params = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });

    if (categoryName === 'Sin categoría' || categoryName === 'Sin categoria') {
      params.set('category_id', 'uncategorized');
    } else {
      const cat = allCategories?.find(
        (c) => c.name.toLowerCase() === categoryName.toLowerCase(),
      );
      if (cat) params.set('category_id', cat.id);
    }

    router.push(`/transactions?${params.toString()}`);
  }

  // ── Dynamic subtitles ─────────────────────────────────────────────────────
  const donutTitle = donutSubtitle(viewPeriod, refDate, weekFilter);
  const incomeTitle = incomeSubtitle(viewPeriod, refDate, weekFilter);
  const lineTitle = lineSubtitle(viewPeriod, refDate, weekFilter);
  const pLabel = periodLabel(viewPeriod, refDate, weekFilter);

  return (
    <div className="space-y-6">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4">
        {/* Row 1: title + period type selector */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Informes</h1>
            <p className="mt-1 text-sm text-gray-500">
              Visualiza tu evolución y optimiza tus decisiones financieras.
            </p>
          </div>
          <PeriodSelector value={viewPeriod} onChange={handlePeriodChange} />
        </div>

        {/* Row 2: date navigator + week pills */}
        <div className="rounded-xl bg-white px-4 py-3 shadow-sm">
          <DateNavigator
            period={viewPeriod}
            refDate={refDate}
            weekFilter={weekFilter}
            onPrev={() => navigate(-1)}
            onNext={() => navigate(1)}
            onReset={handleReset}
            onWeekSelect={handleWeekSelect}
          />
        </div>
      </div>

      {/* ── Evolución del Patrimonio: full width ─────────────────────── */}
      <div className="rounded-xl bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-start justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Evolución del Patrimonio</h2>
            <p className="text-sm text-gray-500">Balance reconstruido — {pLabel}</p>
          </div>
        </div>

        {balanceQuery.isLoading ? (
          <CardSkeleton height="h-80" />
        ) : balanceQuery.isError ? (
          <ErrorCard onRetry={() => balanceQuery.refetch()} />
        ) : balanceQuery.data ? (
          <BalanceEvolutionChart data={balanceQuery.data} />
        ) : null}
      </div>

      {/* ── Two-column grid: Spending donut + Income donut ───────────── */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Gasto por Categoría */}
        <div className="rounded-xl bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-start justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Gasto por Categoría</h2>
              <p className="text-sm text-gray-500">{donutTitle}</p>
            </div>
            <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center overflow-hidden rounded-full border border-gray-200">
              <span className="h-full w-1/2 bg-black" />
              <span className="h-full w-1/2 bg-white" />
            </span>
          </div>

          {spendingQuery.isLoading ? (
            <CardSkeleton />
          ) : spendingQuery.isError ? (
            <ErrorCard onRetry={() => spendingQuery.refetch()} />
          ) : spendingQuery.data ? (
            <SpendingDonutChart
              totalSpending={spendingQuery.data.total_spending}
              categories={spendingQuery.data.categories}
              periodLabel={donutTitle}
              onCategoryClick={handleCategoryClick}
            />
          ) : null}
        </div>

        {/* Ingreso por Categoría */}
        <div className="rounded-xl bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-start justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Ingreso por Categoría</h2>
              <p className="text-sm text-gray-500">{incomeTitle}</p>
            </div>
            <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center overflow-hidden rounded-full border border-gray-200 bg-[#1A5632]">
              <span className="h-3 w-3 rounded-full bg-[#2ECC71]" />
            </span>
          </div>

          {incomeQuery.isLoading ? (
            <CardSkeleton />
          ) : incomeQuery.isError ? (
            <ErrorCard onRetry={() => incomeQuery.refetch()} />
          ) : incomeQuery.data ? (
            <IncomeDonutChart
              totalIncome={incomeQuery.data.total_income}
              categories={incomeQuery.data.categories}
              periodLabel={incomeTitle}
            />
          ) : null}
        </div>
      </div>

      {/* ── Evolución Temporal: full width ───────────────────────────── */}
      <div className="rounded-xl bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-start justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Evolución Temporal</h2>
            <p className="text-sm text-gray-500">{lineTitle}</p>
          </div>
          <div className="flex flex-shrink-0 items-center gap-3 text-xs font-medium">
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-[#1A5632]" />
              <span className="text-gray-600">Ingresos</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-[#2471A3]" />
              <span className="text-gray-600">Gastos</span>
            </span>
          </div>
        </div>

        {incomeExpensesQuery.isLoading ? (
          <CardSkeleton />
        ) : incomeExpensesQuery.isError ? (
          <ErrorCard onRetry={() => incomeExpensesQuery.refetch()} />
        ) : incomeExpensesQuery.data ? (
          <IncomeExpensesLineChart dataPoints={incomeExpensesQuery.data.data_points} />
        ) : null}
      </div>

      {/* ── Sankey: full width ──────────────────────────────────────────── */}
      <div className="rounded-xl bg-white p-6 shadow-sm">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Flujo de Caja</h2>
          <p className="text-sm text-gray-500">
            Recorrido del dinero desde ingresos hasta categorías de gasto.
          </p>
        </div>

        {sankeyQuery.isLoading ? (
          <CardSkeleton height="h-[420px]" />
        ) : sankeyQuery.isError ? (
          <ErrorCard onRetry={() => sankeyQuery.refetch()} />
        ) : sankeyQuery.data ? (
          <CashflowSankeyChart data={sankeyQuery.data} />
        ) : null}
      </div>

      {/* ── Export button ───────────────────────────────────────────────── */}
      <div className="flex justify-end">
        <ExportCSVButton period={apiPeriod} date={apiDateStr} />
      </div>
    </div>
  );
}
