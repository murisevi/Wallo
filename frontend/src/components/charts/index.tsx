/**
 * Lazy-loaded chart exports via next/dynamic.
 * All charts are SSR-disabled to avoid hydration issues with canvas/SVG libraries.
 * Each shows a pulse skeleton while the JS chunk loads.
 */
import dynamic from 'next/dynamic';

function ChartSkeleton({ height = 'h-64' }: { height?: string }) {
  return <div className={`${height} w-full animate-pulse rounded-lg bg-gray-200`} />;
}

export const LazySpendingDonutChart = dynamic(
  () => import('@/components/features/SpendingDonutChart'),
  { loading: () => <ChartSkeleton />, ssr: false },
);

export const LazyIncomeDonutChart = dynamic(
  () => import('@/components/features/IncomeDonutChart'),
  { loading: () => <ChartSkeleton />, ssr: false },
);

export const LazyIncomeExpensesLineChart = dynamic(
  () => import('@/components/features/IncomeExpensesLineChart'),
  { loading: () => <ChartSkeleton height="h-72" />, ssr: false },
);

export const LazyBalanceEvolutionChart = dynamic(
  () => import('@/components/features/BalanceEvolutionChart'),
  { loading: () => <ChartSkeleton height="h-80" />, ssr: false },
);

export const LazyCashflowSankeyChart = dynamic(
  () => import('@/components/features/CashflowSankeyChart'),
  { loading: () => <ChartSkeleton height="h-[420px]" />, ssr: false },
);
