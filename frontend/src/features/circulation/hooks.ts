import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { circulationApi, type LoanQuery } from '@/api/endpoints'
import { catalogKeys } from '@/features/catalog/hooks'

export const circulationKeys = {
  all: ['circulation'] as const,
  loans: (query: LoanQuery) => [...circulationKeys.all, 'loans', query] as const,
  myLoans: (status: string) => [...circulationKeys.all, 'my-loans', status] as const,
  myReservations: () => [...circulationKeys.all, 'my-reservations'] as const,
  myFines: () => [...circulationKeys.all, 'my-fines'] as const,
  reservations: (query: object) => [...circulationKeys.all, 'reservations', query] as const,
  fines: (query: object) => [...circulationKeys.all, 'fines', query] as const,
  stats: () => [...circulationKeys.all, 'stats'] as const,
}

/** Circulation changes ripple into availability counts, so both trees refresh together. */
function useCirculationMutation<TArgs, TResult>(mutationFn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: circulationKeys.all })
      void queryClient.invalidateQueries({ queryKey: catalogKeys.all })
    },
  })
}

export function useLoans(query: LoanQuery) {
  return useQuery({
    queryKey: circulationKeys.loans(query),
    queryFn: () => circulationApi.listLoans(query),
  })
}

export function useMyLoans(status = '') {
  return useQuery({
    queryKey: circulationKeys.myLoans(status),
    queryFn: () => circulationApi.myLoans({ status }),
  })
}

export function useMyReservations() {
  return useQuery({
    queryKey: circulationKeys.myReservations(),
    queryFn: circulationApi.myReservations,
  })
}

export function useMyFines() {
  return useQuery({ queryKey: circulationKeys.myFines(), queryFn: circulationApi.myFines })
}

export function useReservations(query: { status?: string } = {}) {
  return useQuery({
    queryKey: circulationKeys.reservations(query),
    queryFn: () => circulationApi.listReservations(query),
  })
}

export function useFines(query: { status?: string } = {}) {
  return useQuery({
    queryKey: circulationKeys.fines(query),
    queryFn: () => circulationApi.listFines(query),
  })
}

export function useDashboardStats() {
  return useQuery({ queryKey: circulationKeys.stats(), queryFn: circulationApi.dashboardStats })
}

export const useCheckout = () => useCirculationMutation(circulationApi.checkout)
export const useCheckin = () => useCirculationMutation(circulationApi.checkin)
export const useRenew = () => useCirculationMutation(circulationApi.renew)
export const useReserve = () => useCirculationMutation(circulationApi.reserve)
export const useCancelReservation = () => useCirculationMutation(circulationApi.cancelReservation)
export const useFulfilReservation = () => useCirculationMutation(circulationApi.fulfilReservation)
export const usePayFine = () => useCirculationMutation(circulationApi.payFine)
export const useWaiveFine = () =>
  useCirculationMutation(({ id, reason }: { id: number; reason: string }) =>
    circulationApi.waiveFine(id, reason),
  )
