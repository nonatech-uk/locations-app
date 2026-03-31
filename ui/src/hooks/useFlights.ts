import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteFlight, fetchFlight, fetchFlights, updateFlight } from '../api/flights'
import type { FlightUpdate } from '../api/types'

export function useFlights(page: number, perPage: number) {
  return useQuery({
    queryKey: ['flights', page, perPage],
    queryFn: () => fetchFlights(page, perPage),
    staleTime: 5 * 60_000,
  })
}

export function useFlight(id: number | null) {
  return useQuery({
    queryKey: ['flight', id],
    queryFn: () => fetchFlight(id!),
    enabled: id !== null,
    staleTime: 5 * 60_000,
  })
}

export function useUpdateFlight() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: FlightUpdate }) => updateFlight(id, data),
    onSuccess: (_result, { id }) => {
      qc.invalidateQueries({ queryKey: ['flight', id] })
      qc.invalidateQueries({ queryKey: ['flights'] })
    },
  })
}

export function useDeleteFlight() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteFlight(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['flights'] })
    },
  })
}
