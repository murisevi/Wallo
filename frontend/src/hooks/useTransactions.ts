'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { TransactionList } from '@/types';

interface UseTransactionsParams {
  page?: number;
  pageSize?: number;
  accountId?: string;
  search?: string;
  dateFrom?: string;
  dateTo?: string;
  categoryId?: string; // UUID or "uncategorized"
}

export function useTransactions({
  page = 1,
  pageSize = 20,
  accountId,
  search,
  dateFrom,
  dateTo,
  categoryId,
}: UseTransactionsParams = {}) {
  const params = new URLSearchParams();
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  if (accountId) params.set('account_id', accountId);
  if (search) params.set('search', search);
  if (dateFrom) params.set('date_from', dateFrom);
  if (dateTo) params.set('date_to', dateTo);
  if (categoryId) params.set('category_id', categoryId);

  return useQuery<TransactionList>({
    queryKey: ['transactions', { page, pageSize, accountId, search, dateFrom, dateTo, categoryId }],
    queryFn: () => api.get<TransactionList>(`/transactions/?${params.toString()}`),
  });
}
