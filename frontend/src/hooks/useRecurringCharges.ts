'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { recurringApi } from '@/lib/api';

export function useRecurringCharges() {
  return useQuery({
    queryKey: ['recurring-charges'],
    queryFn: () => recurringApi.list(),
    staleTime: 1000 * 60 * 2,
  });
}

export function useRecurringChargeActions() {
  const queryClient = useQueryClient();

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    queryClient.invalidateQueries({ queryKey: ['recurring-charges'] });
  };

  const confirm = useMutation({
    mutationFn: (id: string) => recurringApi.confirm(id),
    onSuccess: invalidate,
  });

  const dismiss = useMutation({
    mutationFn: (id: string) => recurringApi.dismiss(id),
    onSuccess: invalidate,
  });

  const setInstallment = useMutation({
    mutationFn: ({ id, total }: { id: string; total: number }) =>
      recurringApi.setInstallment(id, total),
    onSuccess: invalidate,
  });

  const deny = useMutation({
    mutationFn: (id: string) => recurringApi.delete(id),
    onSuccess: invalidate,
  });

  return { confirm, dismiss, setInstallment, deny };
}
