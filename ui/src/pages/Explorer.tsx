import { useState } from 'react'
import type { LatLngTuple } from 'leaflet'
import LocationMap from '../components/map/LocationMap'
import { useGpsBounds, useGpsPoints } from '../hooks/useGpsPoints'

function formatDate(d: Date): string {
  return d.toISOString().split('T')[0]
}

function defaultRange(): [string, string] {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 7)
  return [formatDate(start), formatDate(end)]
}

export default function Explorer() {
  const [defaults] = useState(defaultRange)
  const [start, setStart] = useState(defaults[0])
  const [end, setEnd] = useState(defaults[1])

  const bounds = useGpsBounds()
  const { data, isLoading, error } = useGpsPoints(start, end)

  const positions: LatLngTuple[] =
    data?.points.map((p) => [p.lat, p.lon] as LatLngTuple) ?? []

  return (
    <div className="flex flex-col h-full">
      {/* Controls bar */}
      <div className="flex items-center gap-4 px-4 py-3 bg-bg-secondary border-b border-border">
        <label className="flex items-center gap-2 text-sm">
          From
          <input
            type="date"
            value={start}
            min={bounds.data?.earliest}
            max={end}
            onChange={(e) => setStart(e.target.value)}
            className="bg-bg-card border border-border rounded px-2 py-1 text-sm text-text-primary"
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          To
          <input
            type="date"
            value={end}
            min={start}
            max={bounds.data?.latest}
            onChange={(e) => setEnd(e.target.value)}
            className="bg-bg-card border border-border rounded px-2 py-1 text-sm text-text-primary"
          />
        </label>

        {data && (
          <span className="text-xs text-text-secondary ml-auto">
            {data.returned_count.toLocaleString()} points
            {data.simplified && (
              <span className="ml-1 text-amber-600" title={`${data.total_count.toLocaleString()} total`}>
                (simplified from {data.total_count.toLocaleString()})
              </span>
            )}
          </span>
        )}
      </div>

      {/* Map area */}
      <div className="flex-1 relative">
        {isLoading && (
          <div className="absolute inset-0 z-[1000] flex items-center justify-center bg-black/40">
            <div className="animate-spin rounded-full h-10 w-10 border-2 border-accent border-t-transparent" />
          </div>
        )}
        {error && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] bg-red-50 text-red-700 border border-red-200 px-4 py-2 rounded text-sm">
            {(error as Error).message}
          </div>
        )}
        <LocationMap positions={positions} />
      </div>
    </div>
  )
}
