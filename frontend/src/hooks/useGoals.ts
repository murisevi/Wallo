// frontend/src/hooks/useGoals.ts
'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { goalsApi } from '@/lib/api';
import type { ContributionCreate, GoalCreate, GoalStatus, GoalUpdate } from '@/types/goals';

export function useGoals(status?: GoalStatus | 'all') {
  return useQuery({
    queryKey: ['goals', status ?? 'all'],
    queryFn: () => goalsApi.list(status ?? 'all'),
    staleTime: 60_000,
  });
}

export function useCreateGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: GoalCreate) => goalsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useUpdateGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: GoalUpdate }) =>
      goalsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useDeleteGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => goalsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useAddContribution() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ContributionCreate }) =>
      goalsApi.addContribution(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      queryClient.invalidateQueries({ queryKey: ['goals', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useGoal(id: string) {
  return useQuery({
    queryKey: ['goals', id],
    queryFn: () => goalsApi.get(id),
    enabled: Boolean(id),
    staleTime: 60_000,
  });
}

export function useGoalContributions(id: string) {
  return useQuery({
    queryKey: ['goals', id, 'contributions'],
    queryFn: () => goalsApi.getContributions(id),
    enabled: Boolean(id),
    staleTime: 60_000,
  });
}
