'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { budgetApi } from '@/lib/api';
import type { BudgetCreate, BudgetUpdate } from '@/types/budget';

export function useBudgetCategories() {
  return useQuery({
    queryKey: ['budget-categories'],
    queryFn: () => budgetApi.getCategories(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useBudgetSummary(month: number, year: number) {
  return useQuery({
    queryKey: ['budgets', month, year],
    queryFn: () => budgetApi.getSummary(month, year),
  });
}

export function useCreateBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: BudgetCreate) => budgetApi.createBudget(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
    },
  });
}

export function useUpdateBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: BudgetUpdate }) =>
      budgetApi.updateBudget(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
    },
  });
}

export function useDeleteBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => budgetApi.deleteBudget(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
    },
  });
}

export function useCopySource(month: number, year: number) {
  return useQuery({
    queryKey: ['budget-copy-source', month, year],
    queryFn: () => budgetApi.getCopySource(month, year),
    retry: false,
  });
}

export function useCopyPreviousBudgets() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ month, year }: { month: number; year: number }) =>
      budgetApi.copyPrevious(month, year),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      queryClient.invalidateQueries({ queryKey: ['budget-copy-source'] });
    },
  });
}
