import { apiImageUrl } from '../../api/client'
import type { FlightSummary } from '../../api/types'
import ImageLightbox from './ImageLightbox'
import { useState, useCallback } from 'react'

const CLASS_SHORT: Record<number, string> = { 1: 'Y', 2: 'J', 3: 'F', 4: 'Y+' }

interface Props {
  flight: FlightSummary
  isSelected: boolean
  onSelect: () => void
}

function FlightImage({ src, fullSrc, alt, onLightbox }: {
  src: string
  fullSrc: string
  alt: string
  onLightbox: (e: React.MouseEvent, src: string, alt: string) => void
}) {
  const [failed, setFailed] = useState(false)
  const handleError = useCallback(() => setFailed(true), [])

  if (failed) {
    return <div className="h-10 w-16 rounded bg-bg-hover flex items-center justify-center text-xs text-text-secondary">—</div>
  }

  return (
    <img
      src={src}
      alt={alt}
      className="h-10 rounded cursor-pointer hover:opacity-80 transition-opacity"
      onError={handleError}
      onClick={(e) => onLightbox(e, fullSrc, alt)}
    />
  )
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
        <td className="px-3 py-2 text-sm text-center">
          {flight.notes ? (
            <svg className="inline-block w-4 h-4 text-text-secondary cursor-help" viewBox="0 0 20 20" fill="currentColor">
              <title>{flight.notes}</title>
              <path fillRule="evenodd" d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0m-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0M9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9" clipRule="evenodd" />
            </svg>
          ) : null}
        </td>
        <td className="px-2 py-1">
          {flight.has_route_image ? (
            <FlightImage
              src={apiImageUrl(`/flights/${flight.id}/images/route/thumb`)}
              fullSrc={apiImageUrl(`/flights/${flight.id}/images/route/full`)}
              alt="Route"
              onLightbox={handleImgClick}
            />
          ) : (
            <div className="h-10 w-16 rounded bg-bg-hover flex items-center justify-center text-xs text-text-secondary">—</div>
          )}
        </td>
        <td className="px-2 py-1">
          {flight.has_aircraft_image ? (
            <FlightImage
              src={apiImageUrl(`/flights/${flight.id}/images/aircraft/thumb`)}
              fullSrc={apiImageUrl(`/flights/${flight.id}/images/aircraft/full`)}
              alt="Aircraft"
              onLightbox={handleImgClick}
            />
          ) : (
            <div className="h-10 w-16 rounded bg-bg-hover flex items-center justify-center text-xs text-text-secondary">—</div>
          )}
        </td>
      </tr>
    </>
  )
}
