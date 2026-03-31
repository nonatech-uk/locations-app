import { useEffect, useState } from 'react'
import { useDeleteFlight, useFlight, useUpdateFlight } from '../../hooks/useFlights'
import { apiImageUrl } from '../../api/client'
import type { FlightUpdate } from '../../api/types'
import ImageLightbox from './ImageLightbox'

const CLASS_LABELS: Record<number, string> = { 1: 'Economy', 2: 'Business', 3: 'First', 4: 'Economy Plus' }
const SEAT_TYPE_LABELS: Record<number, string> = { 1: 'Window', 2: 'Middle', 3: 'Aisle' }
const REASON_LABELS: Record<number, string> = { 1: 'Leisure', 2: 'Business' }

interface Props {
  flightId: number
  onClose: () => void
}

export default function FlightEditPanel({ flightId, onClose }: Props) {
  const { data: flight, isLoading } = useFlight(flightId)
  const mutation = useUpdateFlight()
  const deleteMutation = useDeleteFlight()
  const [form, setForm] = useState<FlightUpdate>({})
  const [lightbox, setLightbox] = useState<{ src: string; alt: string } | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  useEffect(() => {
    if (flight) {
      setForm({
        notes: flight.notes ?? '',
        seat_number: flight.seat_number ?? '',
        seat_type: flight.seat_type ?? undefined,
        flight_class: flight.flight_class ?? undefined,
        flight_reason: flight.flight_reason ?? undefined,
        registration: flight.registration ?? '',
        aircraft_type: flight.aircraft_type ?? '',
        flight_number: flight.flight_number ?? '',
        airline: flight.airline ?? '',
        is_route: flight.is_route ?? false,
        times_flown: flight.times_flown ?? undefined,
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

  const set = (key: keyof FlightUpdate, value: string | number | boolean | undefined) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const inputCls =
    'bg-bg-card border border-border rounded px-2 py-1 text-sm text-text-primary w-full'
  const selectCls = inputCls
  const labelCls = 'text-xs text-text-secondary mb-1'

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
          {flight.dep_airport} &rarr; {flight.arr_airport} &mdash; {flight.is_route ? 'Route Record' : flight.date}
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
          <div>{flight.dep_airport_name ?? flight.dep_airport} ({flight.dep_icao ?? flight.dep_airport})</div>
        </div>
        <div>
          <span className={labelCls}>To</span>
          <div>{flight.arr_airport_name ?? flight.arr_airport} ({flight.arr_icao ?? flight.arr_airport})</div>
        </div>
        <div>
          <span className={labelCls}>Times</span>
          <div>{flight.dep_time ?? '?'} &rarr; {flight.arr_time ?? '?'}</div>
        </div>
        <div>
          <span className={labelCls}>Duration</span>
          <div>{flight.duration ?? '—'}</div>
        </div>
        {flight.distance_km && (
          <div>
            <span className={labelCls}>Distance</span>
            <div>{flight.distance_km.toLocaleString()} km</div>
          </div>
        )}
        {flight.gate_origin && (
          <div>
            <span className={labelCls}>Gate (dep)</span>
            <div>{flight.terminal_origin ? `T${flight.terminal_origin} / ` : ''}{flight.gate_origin}</div>
          </div>
        )}
        {flight.gate_destination && (
          <div>
            <span className={labelCls}>Gate (arr)</span>
            <div>{flight.terminal_destination ? `T${flight.terminal_destination} / ` : ''}{flight.gate_destination}</div>
          </div>
        )}
        {flight.codeshares && (
          <div>
            <span className={labelCls}>Codeshares</span>
            <div>{flight.codeshares}</div>
          </div>
        )}
        <div>
          <span className={labelCls}>Source</span>
          <div>{flight.source ?? '—'}</div>
        </div>
      </div>

      {/* Images */}
      <div className="flex gap-4 mb-4">
        {flight.has_route_image && (
          <img
            src={apiImageUrl(`/flights/${flight.id}/images/route/thumb`)}
            alt="Route"
            className="rounded cursor-pointer hover:opacity-80 transition-opacity"
            onClick={() => setLightbox({ src: apiImageUrl(`/flights/${flight.id}/images/route/full`), alt: 'Route map' })}
          />
        )}
        {flight.has_aircraft_image && (
          <img
            src={apiImageUrl(`/flights/${flight.id}/images/aircraft/thumb`)}
            alt="Aircraft"
            className="rounded cursor-pointer hover:opacity-80 transition-opacity"
            onClick={() => setLightbox({ src: apiImageUrl(`/flights/${flight.id}/images/aircraft/full`), alt: 'Aircraft' })}
          />
        )}
      </div>

      {/* Editable fields */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div>
          <div className={labelCls}>Flight Number</div>
          <input className={inputCls} value={form.flight_number ?? ''} onChange={(e) => set('flight_number', e.target.value)} />
        </div>
        <div>
          <div className={labelCls}>Airline</div>
          <input className={inputCls} value={form.airline ?? ''} onChange={(e) => set('airline', e.target.value)} />
        </div>
        <div>
          <div className={labelCls}>Aircraft Type</div>
          <input className={inputCls} value={form.aircraft_type ?? ''} onChange={(e) => set('aircraft_type', e.target.value)} />
        </div>
        <div>
          <div className={labelCls}>Registration</div>
          <input className={inputCls} value={form.registration ?? ''} onChange={(e) => set('registration', e.target.value)} />
        </div>
        <div>
          <div className={labelCls}>Seat Number</div>
          <input className={inputCls} value={form.seat_number ?? ''} onChange={(e) => set('seat_number', e.target.value)} />
        </div>
        <div>
          <div className={labelCls}>Seat Type</div>
          <select className={selectCls} value={form.seat_type ?? ''} onChange={(e) => set('seat_type', e.target.value ? Number(e.target.value) : undefined)}>
            <option value="">—</option>
            {Object.entries(SEAT_TYPE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>
        <div>
          <div className={labelCls}>Class</div>
          <select className={selectCls} value={form.flight_class ?? ''} onChange={(e) => set('flight_class', e.target.value ? Number(e.target.value) : undefined)}>
            <option value="">—</option>
            {Object.entries(CLASS_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>
        <div>
          <div className={labelCls}>Reason</div>
          <select className={selectCls} value={form.flight_reason ?? ''} onChange={(e) => set('flight_reason', e.target.value ? Number(e.target.value) : undefined)}>
            <option value="">—</option>
            {Object.entries(REASON_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Route record */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="flex items-center gap-2 col-span-2">
          <input
            type="checkbox"
            id="is_route"
            checked={form.is_route ?? false}
            onChange={(e) => set('is_route', e.target.checked)}
            className="accent-accent"
          />
          <label htmlFor="is_route" className="text-sm text-text-secondary">Route record (not a specific flight)</label>
        </div>
        {form.is_route && (
          <div>
            <div className={labelCls}>Times Flown</div>
            <input
              type="number"
              min="1"
              className={inputCls}
              value={form.times_flown ?? ''}
              onChange={(e) => set('times_flown', e.target.value ? Number(e.target.value) : undefined)}
              placeholder="approximate"
            />
          </div>
        )}
      </div>

      {/* Notes */}
      <div className="mb-4">
        <div className={labelCls}>Notes</div>
        <textarea
          className={inputCls + ' h-20 resize-y'}
          value={form.notes ?? ''}
          onChange={(e) => set('notes', e.target.value)}
        />
      </div>

      <div className="flex gap-2 items-center">
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
        <div className="ml-auto">
          {confirmDelete ? (
            <div className="flex gap-2 items-center">
              <span className="text-sm text-red-600">Delete this flight?</span>
              <button
                onClick={() => deleteMutation.mutate(flightId, { onSuccess: onClose })}
                disabled={deleteMutation.isPending}
                className="px-3 py-1.5 rounded bg-red-600 text-white text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Confirm'}
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="px-3 py-1.5 rounded border border-border text-sm text-text-secondary hover:text-text-primary transition-colors"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="px-3 py-1.5 rounded border border-red-300 text-sm text-red-600 hover:bg-red-50 transition-colors"
            >
              Delete
            </button>
          )}
        </div>
      </div>
      </div>
    </div>
  )
}
