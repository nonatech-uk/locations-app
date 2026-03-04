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
