import { useEffect, useRef } from 'react'
import { MapContainer, Polyline, TileLayer, useMap } from 'react-leaflet'
import type { LatLngBoundsExpression, LatLngTuple } from 'leaflet'
import 'leaflet/dist/leaflet.css'

interface Props {
  positions: LatLngTuple[]
}

function FitBounds({ positions }: Props) {
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

const DARK_TILES = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'

export default function LocationMap({ positions }: Props) {
  return (
    <MapContainer
      center={[51.5, -0.1]}
      zoom={5}
      className="h-full w-full rounded-lg"
    >
      <TileLayer url={DARK_TILES} attribution={ATTRIBUTION} />
      {positions.length > 0 && (
        <>
          <Polyline positions={positions} pathOptions={{ color: '#4ecdc4', weight: 2, opacity: 0.8 }} />
          <FitBounds positions={positions} />
        </>
      )}
    </MapContainer>
  )
}
