import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { membersApi } from '@/api/endpoints'
import { circulationKeys } from '@/features/circulation/hooks'

export const memberKeys = {
  all: ['members'] as const,
  list: (query: object) => [...memberKeys.all, 'list', query] as const,
  detail: (id: number) => [...memberKeys.all, 'detail', id] as const,
}

export function useMembers(query: { search?: string; is_suspended?: boolean; page?: number }) {
  return useQuery({
    queryKey: memberKeys.list(query),
    queryFn: () => membersApi.list(query),
  })
}

export function useMember(id: number) {
  return useQuery({
    queryKey: memberKeys.detail(id),
    queryFn: () => membersApi.get(id),
    enabled: Number.isFinite(id),
  })
}

export function useUpdateMember(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof membersApi.update>[1]) => membersApi.update(id, payload),
    onSuccess: () => {
      // Suspending or extending a membership changes what the circulation screens may do,
      // so both trees refresh together.
      void queryClient.invalidateQueries({ queryKey: memberKeys.all })
      void queryClient.invalidateQueries({ queryKey: circulationKeys.all })
    },
  })
}
