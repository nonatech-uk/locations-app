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

// --- Flights ---

export interface FlightSummary {
  id: number
  date: string
  dep_airport: string
  arr_airport: string
  dep_airport_name: string | null
  arr_airport_name: string | null
  flight_number: string | null
  airline: string | null
  aircraft_type: string | null
  registration: string | null
  duration: string | null
  distance_km: number | null
  flight_class: number | null
  seat_number: string | null
  notes: string | null
  has_route_image: boolean
  has_aircraft_image: boolean
}

export interface FlightDetail {
  id: number
  date: string
  flight_number: string | null
  dep_airport: string
  dep_airport_name: string | null
  dep_icao: string | null
  arr_airport: string
  arr_airport_name: string | null
  arr_icao: string | null
  dep_time: string | null
  arr_time: string | null
  duration: string | null
  airline: string | null
  airline_code: string | null
  aircraft_type: string | null
  aircraft_code: string | null
  registration: string | null
  gate_origin: string | null
  gate_destination: string | null
  terminal_origin: string | null
  terminal_destination: string | null
  baggage_claim: string | null
  departure_delay: number | null
  arrival_delay: number | null
  route_distance: number | null
  runway_origin: string | null
  runway_destination: string | null
  codeshares: string | null
  seat_number: string | null
  seat_type: number | null
  flight_class: number | null
  flight_reason: number | null
  notes: string | null
  source: string | null
  gps_matched: boolean
  dep_lat: number | null
  dep_lon: number | null
  arr_lat: number | null
  arr_lon: number | null
  distance_km: number | null
  has_route_image: boolean
  has_aircraft_image: boolean
}

export interface FlightUpdate {
  notes?: string
  seat_number?: string
  seat_type?: number
  flight_class?: number
  flight_reason?: number
  registration?: string
  aircraft_type?: string
  flight_number?: string
  airline?: string
}

export interface FlightListResponse {
  items: FlightSummary[]
  total_count: number
  page: number
  per_page: number
  total_pages: number
}

// --- GA Flights ---

export interface GAFlightSummary {
  id: number
  date: string
  aircraft_type: string | null
  registration: string | null
  captain: string | null
  operating_capacity: string | null
  dep_airport: string | null
  arr_airport: string | null
  dep_time: string | null
  arr_time: string | null
  hours_total: number | null
  exercise: string | null
  is_local: boolean
  has_route_image: boolean
  has_aircraft_image: boolean
}

export interface GAFlightDetail {
  id: number
  date: string
  aircraft_type: string | null
  registration: string | null
  captain: string | null
  operating_capacity: string | null
  dep_airport: string | null
  arr_airport: string | null
  dep_time: string | null
  arr_time: string | null
  hours_sep_pic: number | null
  hours_sep_dual: number | null
  hours_mep_pic: number | null
  hours_mep_dual: number | null
  hours_pic_3: number | null
  hours_dual_3: number | null
  hours_pic_4: number | null
  hours_dual_4: number | null
  hours_instrument: number | null
  hours_as_instructor: number | null
  hours_simulator: number | null
  hours_total: number | null
  instructor: string | null
  exercise: string | null
  comments: string | null
  is_local: boolean
  has_route_image: boolean
  has_aircraft_image: boolean
}

export interface GAFlightUpdate {
  comments?: string
  exercise?: string
  captain?: string
  operating_capacity?: string
}

export interface GAFlightListResponse {
  items: GAFlightSummary[]
  total_count: number
  page: number
  per_page: number
  total_pages: number
}
