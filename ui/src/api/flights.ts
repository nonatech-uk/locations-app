import { apiFetch, apiMutate } from './client'
import type { FlightDetail, FlightListResponse, FlightUpdate } from './types'

export function fetchFlights(page: number, perPage: number): Promise<FlightListResponse> {
  return apiFetch<FlightListResponse>('/flights/', {
    page: String(page),
    per_page: String(perPage),
  })
}

export function fetchFlight(id: number): Promise<FlightDetail> {
  return apiFetch<FlightDetail>(`/flights/${id}`)
}

export function updateFlight(id: number, data: FlightUpdate): Promise<FlightDetail> {
  return apiMutate<FlightDetail>(`/flights/${id}`, 'PATCH', data)
}

export async function deleteFlight(id: number): Promise<void> {
  const url = new URL(`/api/v1/flights/${id}`, window.location.origin)
  const res = await fetch(url.toString(), { method: 'DELETE' })
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
}
