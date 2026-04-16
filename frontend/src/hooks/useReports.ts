'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  BalanceEvolutionResponse,
  IncomeByCategoryResponse,
  IncomeVsExpensesResponse,
  PeriodEnum,
  SankeyResponse,
  SpendingByCategoryResponse,
} from '@/types/reports';

// ---------------------------------------------------------------------------
// Spending by category
// ---------------------------------------------------------------------------

export function useSpendingByCategory(period: PeriodEnum, date?: string) {
  const params = new URLSearchParams({ period });
  if (date) params.set('date', date);

  return useQuery<SpendingByCategoryResponse>({
    queryKey: ['reports', 'spending-by-category', period, date],
    queryFn: () =>
      api.get<SpendingByCategoryResponse>(`/reports/spending-by-category?${params.toString()}`),
  });
}

// ---------------------------------------------------------------------------
// Income vs expenses
// ---------------------------------------------------------------------------

export function useIncomeVsExpenses(period: PeriodEnum, date?: string) {
  const params = new URLSearchParams({ period });
  if (date) params.set('date', date);

  return useQuery<IncomeVsExpensesResponse>({
    queryKey: ['reports', 'income-vs-expenses', period, date],
    queryFn: () =>
      api.get<IncomeVsExpensesResponse>(`/reports/income-vs-expenses?${params.toString()}`),
  });
}

// ---------------------------------------------------------------------------
// Cashflow Sankey
// ---------------------------------------------------------------------------

export function useCashflowSankey(period: PeriodEnum, date?: string) {
  const params = new URLSearchParams({ period });
  if (date) params.set('date', date);

  return useQuery<SankeyResponse>({
    queryKey: ['reports', 'cashflow-sankey', period, date],
    queryFn: () => api.get<SankeyResponse>(`/reports/cashflow-sankey?${params.toString()}`),
  });
}

// ---------------------------------------------------------------------------
// Balance evolution
// ---------------------------------------------------------------------------

export function useBalanceEvolution(period: PeriodEnum, date?: string) {
  const params = new URLSearchParams({ period });
  if (date) params.set('date', date);

  return useQuery<BalanceEvolutionResponse>({
    queryKey: ['reports', 'balance-evolution', period, date],
    queryFn: () =>
      api.get<BalanceEvolutionResponse>(`/reports/balance-evolution?${params.toString()}`),
  });
}

// ---------------------------------------------------------------------------
// Income by category
// ---------------------------------------------------------------------------

export function useIncomeByCategory(period: PeriodEnum, date?: string) {
  const params = new URLSearchParams({ period });
  if (date) params.set('date', date);

  return useQuery<IncomeByCategoryResponse>({
    queryKey: ['reports', 'income-by-category', period, date],
    queryFn: () =>
      api.get<IncomeByCategoryResponse>(`/reports/income-by-category?${params.toString()}`),
  });
}

// ---------------------------------------------------------------------------
// Export CSV — mutation that triggers a file download
// ---------------------------------------------------------------------------

export function useExportCSV() {
  return useMutation({
    mutationFn: async ({ period, date }: { period: PeriodEnum; date?: string }) => {
      const params = new URLSearchParams({ period });
      if (date) params.set('date', date);

      const blob = await api.getBlob(`/reports/export-csv?${params.toString()}`);

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const today = new Date().toISOString().slice(0, 10);
      a.download = `wallo_transactions_${period}_${today}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  });
}
