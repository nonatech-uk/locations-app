export interface GpsPoint {
  lat: number
  lon: number
  ts: string
  speed_mph: number | null
  altitude_m: number | null
}

export interface GpsPointsResponse {
  points: GpsPoint[]
  total_count: number
  returned_count: number
  simplified: boolean
}

export interface GpsBoundsResponse {
  earliest: string
  latest: string
  total_points: number
}

export interface OverviewStats {
  gps_points: number
  flights: number
  skiing_days: number
  ga_flights: number
}

// --- Places ---

export interface PlaceType {
  id: number
  name: string
}

export interface PlaceTypeListResponse {
  items: PlaceType[]
  total_count: number
}

export interface PlaceSummary {
  id: number
  name: string
  place_type_id: number
  place_type_name: string
  lat: number
  lon: number
  distance_m: number
  date_from: string | null
  date_to: string | null
  notes: string | null
}

export interface PlaceListResponse {
  items: PlaceSummary[]
  total_count: number
  page: number
  per_page: number
  total_pages: number
}

export interface PlaceLookupResult {
  place: PlaceSummary | null
  distance_m: number | null
  source: string
}

export interface MapBounds {
  south: number
  west: number
  north: number
  east: number
}

export interface PlaceCreate {
  name: string
  place_type_id: number
  lat: number
  lon: number
  distance_m?: number
  date_from?: string | null
  date_to?: string | null
  notes?: string | null
}

export interface PlaceUpdate {
  name?: string
  place_type_id?: number
  lat?: number
  lon?: number
  distance_m?: number
  date_from?: string | null
  date_to?: string | null
  notes?: string | null
}
