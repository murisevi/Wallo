'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Dashboard } from '@/types';

export function useDashboard() {
  return useQuery<Dashboard>({
    queryKey: ['dashboard'],
    queryFn: () => api.get<Dashboard>('/dashboard/'),
  });
}
