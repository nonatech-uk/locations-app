import { apiFetch, apiMutate } from './client'
import type { GAFlightDetail, GAFlightListResponse, GAFlightUpdate } from './types'

export function fetchGAFlights(page: number, perPage: number): Promise<GAFlightListResponse> {
  return apiFetch<GAFlightListResponse>('/ga/', {
    page: String(page),
    per_page: String(perPage),
  })
}

export function fetchGAFlight(id: number): Promise<GAFlightDetail> {
  return apiFetch<GAFlightDetail>(`/ga/${id}`)
}

export function updateGAFlight(id: number, data: GAFlightUpdate): Promise<GAFlightDetail> {
  return apiMutate<GAFlightDetail>(`/ga/${id}`, 'PATCH', data)
}
