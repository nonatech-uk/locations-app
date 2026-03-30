import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchGAFlight, fetchGAFlights, updateGAFlight } from '../api/ga'
import type { GAFlightUpdate } from '../api/types'

export function useGAFlights(page: number, perPage: number) {
  return useQuery({
    queryKey: ['ga-flights', page, perPage],
    queryFn: () => fetchGAFlights(page, perPage),
    staleTime: 5 * 60_000,
  })
}

export function useGAFlight(id: number | null) {
  return useQuery({
    queryKey: ['ga-flight', id],
    queryFn: () => fetchGAFlight(id!),
    enabled: id !== null,
    staleTime: 5 * 60_000,
  })
}

export function useUpdateGAFlight() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: GAFlightUpdate }) => updateGAFlight(id, data),
    onSuccess: (_result, { id }) => {
      qc.invalidateQueries({ queryKey: ['ga-flight', id] })
      qc.invalidateQueries({ queryKey: ['ga-flights'] })
    },
  })
}
