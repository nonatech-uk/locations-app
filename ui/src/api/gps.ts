import { apiFetch } from './client'
import type { GpsBoundsResponse, GpsPointsResponse } from './types'

export function fetchGpsPoints(start: string, end: string) {
  return apiFetch<GpsPointsResponse>('/gps/points', { start, end })
}

export function fetchGpsBounds() {
  return apiFetch<GpsBoundsResponse>('/gps/bounds')
}
