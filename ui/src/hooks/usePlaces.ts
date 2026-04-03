import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createPlace,
  createPlaceType,
  deletePlace,
  deletePlaceType,
  fetchPlace,
  fetchPlaces,
  fetchPlacesInBounds,
  fetchPlaceTypes,
  lookupPlace,
  updatePlace,
  updatePlaceType,
} from '../api/places'
import type { MapBounds, PlaceCreate, PlaceUpdate } from '../api/types'

export function usePlacesInBounds(bounds: MapBounds | null) {
  return useQuery({
    queryKey: ['places-in-bounds', bounds?.south, bounds?.west, bounds?.north, bounds?.east],
    queryFn: () => fetchPlacesInBounds(bounds!),
    enabled: bounds !== null,
    staleTime: 60_000,
  })
}

export function usePlaces(page: number, perPage: number) {
  return useQuery({
    queryKey: ['places', page, perPage],
    queryFn: () => fetchPlaces(page, perPage),
    staleTime: 5 * 60_000,
  })
}

export function usePlace(id: number | null) {
  return useQuery({
    queryKey: ['place', id],
    queryFn: () => fetchPlace(id!),
    enabled: id !== null,
    staleTime: 5 * 60_000,
  })
}

export function usePlaceLookup(lat: number | null, lon: number | null, dt?: string) {
  return useQuery({
    queryKey: ['place-lookup', lat, lon, dt],
    queryFn: () => lookupPlace(lat!, lon!, dt),
    enabled: lat !== null && lon !== null,
    staleTime: 5 * 60_000,
  })
}

export function usePlaceTypes() {
  return useQuery({
    queryKey: ['place-types'],
    queryFn: fetchPlaceTypes,
    staleTime: 30 * 60_000,
  })
}

export function useCreatePlace() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: PlaceCreate) => createPlace(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['places'] })
      qc.invalidateQueries({ queryKey: ['place-lookup'] })
    },
  })
}

export function useUpdatePlace() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: PlaceUpdate }) => updatePlace(id, data),
    onSuccess: (_result, { id }) => {
      qc.invalidateQueries({ queryKey: ['place', id] })
      qc.invalidateQueries({ queryKey: ['places'] })
      qc.invalidateQueries({ queryKey: ['place-lookup'] })
    },
  })
}

export function useDeletePlace() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deletePlace(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['places'] })
      qc.invalidateQueries({ queryKey: ['place-lookup'] })
    },
  })
}

export function useCreatePlaceType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => createPlaceType(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['place-types'] })
    },
  })
}

export function useUpdatePlaceType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => updatePlaceType(id, name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['place-types'] })
      qc.invalidateQueries({ queryKey: ['places'] })
    },
  })
}

export function useDeletePlaceType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deletePlaceType(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['place-types'] })
    },
  })
}
