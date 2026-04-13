'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { categoryApi } from '@/lib/api';
import type { Category } from '@/types/categories';

/** Fetch all system + user-custom categories. Cached for 10 minutes. */
export function useCategories() {
  return useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: () => categoryApi.getCategories(),
    staleTime: 1000 * 60 * 10,
  });
}

/** Mutation to correct a transaction's category (active-learning feedback).
 *
 * On success, invalidates the 'transactions' query so the list refreshes
 * and shows the updated category immediately.
 */
export function useCorrectionMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      transactionId,
      categoryId,
    }: {
      transactionId: string;
      categoryId: string;
    }) => categoryApi.correctTransactionCategory(transactionId, categoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    },
  });
}
