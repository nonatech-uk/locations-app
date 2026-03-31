import { apiImageUrl } from '../../api/client'
import type { FlightSummary } from '../../api/types'
import ImageLightbox from './ImageLightbox'
import { useState } from 'react'

const CLASS_SHORT: Record<number, string> = { 1: 'Y', 2: 'J', 3: 'F', 4: 'Y+' }

interface Props {
  flight: FlightSummary
  isSelected: boolean
  onSelect: () => void
}

export default function FlightRow({ flight, isSelected, onSelect }: Props) {
  const [lightbox, setLightbox] = useState<{ src: string; alt: string } | null>(null)
  const isRoute = flight.is_route
  const isFuture = !isRoute && flight.date > new Date().toISOString().split('T')[0]

  const handleImgClick = (e: React.MouseEvent, src: string, alt: string) => {
    e.stopPropagation()
    setLightbox({ src, alt })
  }

  return (
    <>
      {lightbox && (
        <ImageLightbox src={lightbox.src} alt={lightbox.alt} onClose={() => setLightbox(null)} />
      )}
      <tr
        onClick={onSelect}
        className={`cursor-pointer border-b border-border transition-colors ${
          isRoute ? 'border-l-2 border-l-blue-500' : isFuture ? 'border-l-2 border-l-amber-500' : ''
        } ${
          isSelected
            ? 'bg-accent/10'
            : isRoute
              ? 'bg-blue-50 hover:bg-blue-100/60'
              : isFuture
                ? 'bg-amber-50 hover:bg-amber-100/60'
                : 'hover:bg-bg-hover'
        }`}
      >
        <td className="px-3 py-2 text-sm whitespace-nowrap">
          {isRoute ? (
            <>
              <span className="text-blue-600 text-xs uppercase tracking-wider">Route</span>
              {flight.times_flown && (
                <span className="ml-1.5 text-[10px] text-text-secondary">&times;{flight.times_flown}</span>
              )}
            </>
          ) : (
            <>
              {flight.date}
              {isFuture && <span className="ml-1.5 text-[10px] text-amber-600 uppercase tracking-wider">upcoming</span>}
            </>
          )}
        </td>
        <td className="px-3 py-2 text-sm">
          <span className="text-accent font-medium">{flight.dep_airport}</span>
          <span className="text-text-secondary mx-1">&rarr;</span>
          <span className="text-accent font-medium">{flight.arr_airport}</span>
        </td>
        <td className="px-3 py-2 text-sm">{flight.flight_number ?? '—'}</td>
        <td className="px-3 py-2 text-sm text-text-secondary">{flight.airline ?? '—'}</td>
        <td className="px-3 py-2 text-sm text-text-secondary">{flight.aircraft_type ?? '—'}</td>
        <td className="px-3 py-2 text-sm whitespace-nowrap">{flight.duration ?? '—'}</td>
        <td className="px-3 py-2 text-sm text-center">
          {flight.flight_class ? CLASS_SHORT[flight.flight_class] ?? '?' : '—'}
        </td>
        <td className="px-3 py-2 text-sm text-text-secondary max-w-[200px] truncate">
          {flight.notes ?? ''}
        </td>
        <td className="px-2 py-1">
          {flight.has_route_image ? (
            <img
              src={apiImageUrl(`/flights/${flight.id}/images/route/thumb`)}
              alt="Route"
              className="h-10 rounded cursor-pointer hover:opacity-80 transition-opacity"
              onClick={(e) =>
                handleImgClick(e, apiImageUrl(`/flights/${flight.id}/images/route/full`), 'Route map')
              }
            />
          ) : (
            <div className="h-10 w-16 rounded bg-bg-hover flex items-center justify-center text-xs text-text-secondary">—</div>
          )}
        </td>
        <td className="px-2 py-1">
          {flight.has_aircraft_image ? (
            <img
              src={apiImageUrl(`/flights/${flight.id}/images/aircraft/thumb`)}
              alt="Aircraft"
              className="h-10 rounded cursor-pointer hover:opacity-80 transition-opacity"
              onClick={(e) =>
                handleImgClick(e, apiImageUrl(`/flights/${flight.id}/images/aircraft/full`), 'Aircraft')
              }
            />
          ) : (
            <div className="h-10 w-16 rounded bg-bg-hover flex items-center justify-center text-xs text-text-secondary">—</div>
          )}
        </td>
      </tr>
    </>
  )
}
