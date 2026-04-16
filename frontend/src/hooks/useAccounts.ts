'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AccountSummary } from '@/types';

export function useAccounts() {
  return useQuery<AccountSummary[]>({
    queryKey: ['accounts'],
    queryFn: () => api.get<AccountSummary[]>('/banking/accounts'),
    staleTime: 1000 * 60 * 5, // 5 min — accounts rarely change
  });
}
