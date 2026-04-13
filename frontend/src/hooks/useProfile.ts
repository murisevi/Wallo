'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { UserProfile, UserProfileUpdate } from '@/types/settings';

export function useProfile() {
  return useQuery<UserProfile>({
    queryKey: ['profile'],
    queryFn: () => api.get<UserProfile>('/auth/profile'),
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: UserProfileUpdate) => api.patch<UserProfile>('/auth/profile', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
  });
}
