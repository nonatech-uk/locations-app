import { useEffect, useState } from 'react'
import { useGAFlight, useUpdateGAFlight } from '../../hooks/useGAFlights'
import { apiImageUrl } from '../../api/client'
import type { GAFlightUpdate } from '../../api/types'
import ImageLightbox from '../flights/ImageLightbox'

interface Props {
  flightId: number
  onClose: () => void
}

function HoursRow({ label, value }: { label: string; value: number | null }) {
  if (!value || value === 0) return null
  return (
    <div>
      <span className="text-xs text-text-secondary">{label}</span>
      <div>{value.toFixed(2)}</div>
    </div>
  )
}

export default function GAFlightEditPanel({ flightId, onClose }: Props) {
  const { data: flight, isLoading } = useGAFlight(flightId)
  const mutation = useUpdateGAFlight()
  const [form, setForm] = useState<GAFlightUpdate>({})
  const [lightbox, setLightbox] = useState<{ src: string; alt: string } | null>(null)

  useEffect(() => {
    if (flight) {
      setForm({
        comments: flight.comments ?? '',
        exercise: flight.exercise ?? '',
        captain: flight.captain ?? '',
        operating_capacity: flight.operating_capacity ?? '',
      })
    }
  }, [flight])

  if (isLoading || !flight) {
    return (
      <div className="fixed inset-0 z-[1500] flex items-center justify-center bg-black/60" onClick={onClose}>
        <div className="bg-bg-secondary border border-border rounded-lg p-10 shadow-lg">
          <div className="animate-spin rounded-full h-10 w-10 border-2 border-accent border-t-transparent" />
        </div>
      </div>
    )
  }

  const handleSave = () => {
    mutation.mutate({ id: flightId, data: form })
  }

  const set = (key: keyof GAFlightUpdate, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const inputCls =
    'bg-bg-card border border-border rounded px-2 py-1 text-sm text-text-primary w-full'
  const labelCls = 'text-xs text-text-secondary mb-1'

  const routeLabel = flight.is_local
    ? flight.dep_airport
    : `${flight.dep_airport} → ${flight.arr_airport}`

  return (
    <div className="fixed inset-0 z-[1500] flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-bg-secondary border border-border rounded-lg p-5 w-[90vw] max-w-4xl max-h-[85vh] overflow-y-auto shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        {lightbox && (
          <ImageLightbox src={lightbox.src} alt={lightbox.alt} onClose={() => setLightbox(null)} />
        )}

        <div className="flex items-center justify-between mb-4">
          <h3 className="text-accent font-semibold">
            {routeLabel} &mdash; {flight.date}
            {flight.is_local && (
              <span className="ml-2 text-xs text-text-secondary font-normal">Local</span>
            )}
          </h3>
          <button
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary text-lg"
          >
            &times;
          </button>
        </div>

        {/* Read-only info */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4 text-sm">
          <div>
            <span className={labelCls}>From</span>
            <div>{flight.dep_airport ?? '—'}</div>
          </div>
          <div>
            <span className={labelCls}>To</span>
            <div>{flight.arr_airport ?? '—'}</div>
          </div>
          <div>
            <span className={labelCls}>Times</span>
            <div>{flight.dep_time ?? '?'} &rarr; {flight.arr_time ?? '?'}</div>
          </div>
          <div>
            <span className={labelCls}>Aircraft</span>
            <div>{flight.aircraft_type ?? '—'} {flight.registration ?? ''}</div>
          </div>
          {flight.instructor && (
            <div>
              <span className={labelCls}>Instructor</span>
              <div>{flight.instructor}</div>
            </div>
          )}
        </div>

        {/* Hours breakdown */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4 text-sm">
          <HoursRow label="SEP PIC" value={flight.hours_sep_pic} />
          <HoursRow label="SEP Dual" value={flight.hours_sep_dual} />
          <HoursRow label="MEP PIC" value={flight.hours_mep_pic} />
          <HoursRow label="MEP Dual" value={flight.hours_mep_dual} />
          <HoursRow label="Instrument" value={flight.hours_instrument} />
          <HoursRow label="As Instructor" value={flight.hours_as_instructor} />
          <HoursRow label="Simulator" value={flight.hours_simulator} />
          <div>
            <span className={labelCls}>Total Hours</span>
            <div className="font-medium">{flight.hours_total?.toFixed(2) ?? '—'}</div>
          </div>
        </div>

        {/* Images */}
        <div className="flex gap-4 mb-4">
          {flight.has_route_image && (
            <img
              src={apiImageUrl(`/ga/${flight.id}/images/route/thumb`)}
              alt="Route"
              className="rounded cursor-pointer hover:opacity-80 transition-opacity"
              onClick={() => setLightbox({ src: apiImageUrl(`/ga/${flight.id}/images/route/full`), alt: 'Route map' })}
            />
          )}
          {flight.has_aircraft_image && (
            <img
              src={apiImageUrl(`/ga/${flight.id}/images/aircraft/thumb`)}
              alt="Aircraft"
              className="rounded cursor-pointer hover:opacity-80 transition-opacity"
              onClick={() => setLightbox({ src: apiImageUrl(`/ga/${flight.id}/images/aircraft/full`), alt: 'Aircraft' })}
            />
          )}
        </div>

        {/* Editable fields */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <div>
            <div className={labelCls}>Captain</div>
            <input className={inputCls} value={form.captain ?? ''} onChange={(e) => set('captain', e.target.value)} />
          </div>
          <div>
            <div className={labelCls}>Capacity</div>
            <select
              className={inputCls}
              value={form.operating_capacity ?? ''}
              onChange={(e) => set('operating_capacity', e.target.value)}
            >
              <option value="">—</option>
              <option value="PUT">PUT (Student)</option>
              <option value="P1">P1 (PIC)</option>
              <option value="P2">P2 (Co-Pilot)</option>
            </select>
          </div>
          <div className="col-span-2">
            <div className={labelCls}>Exercise</div>
            <input className={inputCls} value={form.exercise ?? ''} onChange={(e) => set('exercise', e.target.value)} />
          </div>
        </div>

        <div className="mb-4">
          <div className={labelCls}>Comments</div>
          <textarea
            className={inputCls + ' h-20 resize-y'}
            value={form.comments ?? ''}
            onChange={(e) => set('comments', e.target.value)}
          />
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={mutation.isPending}
            className="px-4 py-1.5 rounded bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-50 transition-colors"
          >
            {mutation.isPending ? 'Saving...' : 'Save'}
          </button>
          {mutation.isSuccess && (
            <span className="text-sm text-green-600 self-center">Saved</span>
          )}
          {mutation.isError && (
            <span className="text-sm text-red-600 self-center">
              {(mutation.error as Error).message}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
