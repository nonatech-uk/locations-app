import { useQuery } from '@tanstack/react-query'
import { fetchGpsBounds, fetchGpsPoints } from '../api/gps'

export function useGpsPoints(start: string, end: string) {
  return useQuery({
    queryKey: ['gps-points', start, end],
    queryFn: () => fetchGpsPoints(start, end),
    enabled: !!start && !!end,
  })
}

export function useGpsBounds() {
  return useQuery({
    queryKey: ['gps-bounds'],
    queryFn: fetchGpsBounds,
  })
}
