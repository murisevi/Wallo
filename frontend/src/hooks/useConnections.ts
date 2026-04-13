'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { BankConnection } from '@/types/settings';

export function useConnections() {
  return useQuery<BankConnection[]>({
    queryKey: ['connections'],
    queryFn: () => api.get<BankConnection[]>('/banking/connections'),
  });
}

export function useDisconnectBank() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (connectionId: string) =>
      api.delete<void>(`/banking/connections/${connectionId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
}
