import { useCallback, useEffect, useRef } from 'react'
import { Circle, MapContainer, Polyline, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import type { LatLngBoundsExpression, LatLngTuple } from 'leaflet'
import type { PlaceSummary, MapBounds } from '../../api/types'
import 'leaflet/dist/leaflet.css'

interface Props {
  positions: LatLngTuple[]
  places?: PlaceSummary[]
  onBoundsChange?: (bounds: MapBounds) => void
  onMapRightClick?: (latlng: { lat: number; lon: number }) => void
  onPlaceClick?: (placeId: number) => void
}

const PLACE_COLORS: Record<string, string> = {
  Home: '#10b981',
  Office: '#3b82f6',
  Airport: '#8b5cf6',
  Restaurant: '#f59e0b',
  Hotel: '#ec4899',
  Pub: '#f97316',
}
const DEFAULT_PLACE_COLOR = '#6b7280'

function placeColor(typeName: string): string {
  return PLACE_COLORS[typeName] ?? DEFAULT_PLACE_COLOR
}

function FitBounds({ positions }: { positions: LatLngTuple[] }) {
  const map = useMap()
  const prev = useRef<string>('')

  useEffect(() => {
    if (positions.length === 0) return
    const key = `${positions.length}-${positions[0][0]}-${positions[positions.length - 1][0]}`
    if (key === prev.current) return
    prev.current = key
    map.fitBounds(positions as LatLngBoundsExpression, { padding: [30, 30] })
  }, [positions, map])

  return null
}

function MapEvents({
  onBoundsChange,
  onMapRightClick,
}: {
  onBoundsChange?: (bounds: MapBounds) => void
  onMapRightClick?: (latlng: { lat: number; lon: number }) => void
}) {
  const reportBounds = useCallback(
    (map: L.Map) => {
      if (!onBoundsChange) return
      const b = map.getBounds()
      onBoundsChange({
        south: b.getSouth(),
        west: b.getWest(),
        north: b.getNorth(),
        east: b.getEast(),
      })
    },
    [onBoundsChange],
  )

  const map = useMapEvents({
    moveend: () => reportBounds(map),
    zoomend: () => reportBounds(map),
    contextmenu: (e) => {
      if (onMapRightClick) {
        onMapRightClick({ lat: e.latlng.lat, lon: e.latlng.lng })
      }
    },
  })

  // Report initial bounds once map is ready
  const initialized = useRef(false)
  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true
      reportBounds(map)
    }
  }, [map, reportBounds])

  return null
}

const LIGHT_TILES = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'

export default function LocationMap({ positions, places, onBoundsChange, onMapRightClick, onPlaceClick }: Props) {
  return (
    <MapContainer
      center={[51.5, -0.1]}
      zoom={5}
      className="h-full w-full rounded-lg"
    >
      <TileLayer url={LIGHT_TILES} attribution={ATTRIBUTION} />
      <MapEvents onBoundsChange={onBoundsChange} onMapRightClick={onMapRightClick} />
      {positions.length > 0 && (
        <>
          <Polyline positions={positions} pathOptions={{ color: '#4f46e5', weight: 2, opacity: 0.8 }} />
          <FitBounds positions={positions} />
        </>
      )}
      {places?.map((place) => (
        <Circle
          key={place.id}
          center={[place.lat, place.lon]}
          radius={place.distance_m}
          pathOptions={{
            color: placeColor(place.place_type_name),
            fillColor: placeColor(place.place_type_name),
            fillOpacity: 0.15,
            weight: 2,
          }}
          eventHandlers={{
            click: (e) => {
              e.originalEvent.stopPropagation()
              onPlaceClick?.(place.id)
            },
          }}
        >
          <Tooltip direction="top" offset={[0, -10]} opacity={0.9}>
            <span className="text-xs font-medium">{place.name}</span>
            <span className="text-xs text-gray-500 ml-1">({place.place_type_name})</span>
          </Tooltip>
        </Circle>
      ))}
    </MapContainer>
  )
}
