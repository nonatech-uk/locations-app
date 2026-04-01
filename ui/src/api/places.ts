import { apiFetch, apiMutate } from './client'
import type {
  PlaceCreate,
  PlaceListResponse,
  PlaceLookupResult,
  PlaceSummary,
  PlaceType,
  PlaceTypeListResponse,
  PlaceUpdate,
} from './types'

export function fetchPlaces(
  page: number,
  perPage: number,
  placeTypeId?: number,
): Promise<PlaceListResponse> {
  const params: Record<string, string> = {
    page: String(page),
    per_page: String(perPage),
  }
  if (placeTypeId !== undefined) params.place_type_id = String(placeTypeId)
  return apiFetch<PlaceListResponse>('/places/', params)
}

export function lookupPlace(
  lat: number,
  lon: number,
  dt?: string,
): Promise<PlaceLookupResult> {
  const params: Record<string, string> = {
    lat: String(lat),
    lon: String(lon),
  }
  if (dt) params.dt = dt
  return apiFetch<PlaceLookupResult>('/places/lookup', params)
}

export function fetchPlace(id: number): Promise<PlaceSummary> {
  return apiFetch<PlaceSummary>(`/places/${id}`)
}

export function createPlace(data: PlaceCreate): Promise<PlaceSummary> {
  return apiMutate<PlaceSummary>('/places/', 'POST', data)
}

export function updatePlace(id: number, data: PlaceUpdate): Promise<PlaceSummary> {
  return apiMutate<PlaceSummary>(`/places/${id}`, 'PATCH', data)
}

export async function deletePlace(id: number): Promise<void> {
  const url = new URL(`/api/v1/places/${id}`, window.location.origin)
  const res = await fetch(url.toString(), { method: 'DELETE' })
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
}

export function fetchPlaceTypes(): Promise<PlaceTypeListResponse> {
  return apiFetch<PlaceTypeListResponse>('/place-types/')
}

export function createPlaceType(name: string): Promise<PlaceType> {
  return apiMutate<PlaceType>('/place-types/', 'POST', { name })
}

export function updatePlaceType(id: number, name: string): Promise<PlaceType> {
  return apiMutate<PlaceType>(`/place-types/${id}`, 'PATCH', { name })
}

export async function deletePlaceType(id: number): Promise<void> {
  const url = new URL(`/api/v1/place-types/${id}`, window.location.origin)
  const res = await fetch(url.toString(), { method: 'DELETE' })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `API error: ${res.status}`)
  }
}
