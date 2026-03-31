import { useState } from 'react'
import { apiImageUrl } from '../../api/client'
import type { GAFlightSummary } from '../../api/types'
import ImageLightbox from '../flights/ImageLightbox'

const CAP_LABELS: Record<string, string> = { PUT: 'Student', P1: 'PIC', P2: 'Co-Pilot' }

interface Props {
  flight: GAFlightSummary
  isSelected: boolean
  onSelect: () => void
}

export default function GAFlightRow({ flight, isSelected, onSelect }: Props) {
  const [lightbox, setLightbox] = useState<{ src: string; alt: string } | null>(null)

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
          isSelected ? 'bg-accent/10' : 'hover:bg-bg-hover'
        }`}
      >
        <td className="px-3 py-2 text-sm whitespace-nowrap">{flight.date}</td>
        <td className="px-3 py-2 text-sm">
          {flight.is_local ? (
            <span className="text-accent font-medium">{flight.dep_airport}</span>
          ) : (
            <>
              <span className="text-accent font-medium">{flight.dep_airport}</span>
              <span className="text-text-secondary mx-1">&rarr;</span>
              <span className="text-accent font-medium">{flight.arr_airport}</span>
            </>
          )}
        </td>
        <td className="px-3 py-2 text-sm">{flight.aircraft_type ?? '—'}</td>
        <td className="px-3 py-2 text-sm text-text-secondary">{flight.registration ?? '—'}</td>
        <td className="px-3 py-2 text-sm text-text-secondary">{flight.captain ?? '—'}</td>
        <td className="px-3 py-2 text-sm text-center">
          {flight.operating_capacity ? CAP_LABELS[flight.operating_capacity] ?? flight.operating_capacity : '—'}
        </td>
        <td className="px-3 py-2 text-sm whitespace-nowrap text-right tabular-nums">
          {flight.hours_total?.toFixed(1) ?? '—'}
        </td>
        <td className="px-3 py-2 text-sm text-text-secondary max-w-[200px] truncate">
          {flight.exercise ?? ''}
        </td>
        <td className="px-2 py-1">
          {flight.has_route_image ? (
            <img
              src={apiImageUrl(`/ga/${flight.id}/images/route/thumb`)}
              alt="Route"
              className="h-10 rounded cursor-pointer hover:opacity-80 transition-opacity"
              onClick={(e) =>
                handleImgClick(e, apiImageUrl(`/ga/${flight.id}/images/route/full`), 'Route map')
              }
            />
          ) : (
            <div className="h-10 w-16 rounded bg-bg-hover flex items-center justify-center text-xs text-text-secondary">—</div>
          )}
        </td>
        <td className="px-2 py-1">
          {flight.has_aircraft_image ? (
            <img
              src={apiImageUrl(`/ga/${flight.id}/images/aircraft/thumb`)}
              alt="Aircraft"
              className="h-10 rounded cursor-pointer hover:opacity-80 transition-opacity"
              onClick={(e) =>
                handleImgClick(e, apiImageUrl(`/ga/${flight.id}/images/aircraft/full`), 'Aircraft')
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
