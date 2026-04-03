import { useEffect, useState } from 'react'
import { usePlace, usePlaceTypes, useCreatePlace, useUpdatePlace, useDeletePlace } from '../../hooks/usePlaces'
import type { PlaceCreate, PlaceUpdate } from '../../api/types'
import PlaceTypesPanel from './PlaceTypesPanel'

interface Props {
  placeId: number | null
  onCreate?: { name: string; lat: number; lon: number }
  onClose: () => void
}

const JOURNAL_SYNC_URL = 'https://journal.mees.st/api/v1/places/sync'

export default function PlaceEditPanel({ placeId, onCreate, onClose }: Props) {
  const isEdit = placeId !== null
  const { data: place, isLoading: placeLoading } = usePlace(placeId)
  const { data: placeTypes } = usePlaceTypes()
  const createMutation = useCreatePlace()
  const updateMutation = useUpdatePlace()
  const deleteMutation = useDeletePlace()

  const [form, setForm] = useState<PlaceCreate>({
    name: onCreate?.name ?? '',
    place_type_id: 0,
    lat: onCreate?.lat ?? 0,
    lon: onCreate?.lon ?? 0,
    distance_m: 200,
    date_from: null,
    date_to: null,
    notes: null,
  })
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [saved, setSaved] = useState(false)
  const [showTypes, setShowTypes] = useState(false)

  useEffect(() => {
    if (place) {
      setForm({
        name: place.name,
        place_type_id: place.place_type_id,
        lat: place.lat,
        lon: place.lon,
        distance_m: place.distance_m,
        date_from: place.date_from,
        date_to: place.date_to,
        notes: place.notes,
      })
    }
  }, [place])

  useEffect(() => {
    if (!isEdit && placeTypes?.items.length && form.place_type_id === 0) {
      setForm((prev) => ({ ...prev, place_type_id: placeTypes.items[0].id }))
    }
  }, [placeTypes, isEdit, form.place_type_id])

  const triggerJournalSync = async () => {
    setSyncing(true)
    try {
      await fetch(JOURNAL_SYNC_URL, { method: 'POST', credentials: 'include' })
    } catch {
      // sync failure is non-blocking
    } finally {
      setSyncing(false)
    }
  }

  const handleSave = async () => {
    if (isEdit) {
      const update: PlaceUpdate = {
        name: form.name,
        place_type_id: form.place_type_id,
        distance_m: form.distance_m,
        date_from: form.date_from,
        date_to: form.date_to,
        notes: form.notes,
      }
      updateMutation.mutate(
        { id: placeId, data: update },
        {
          onSuccess: async () => {
            await triggerJournalSync()
            setSaved(true)
            tryCloseTab()
          },
        },
      )
    } else {
      createMutation.mutate(form, {
        onSuccess: async () => {
          await triggerJournalSync()
          setSaved(true)
          tryCloseTab()
        },
      })
    }
  }

  const tryCloseTab = () => {
    try {
      window.close()
    } catch {
      // tab wasn't opened by script — stay on page with success message
    }
  }

  if (isEdit && (placeLoading || !place)) {
    return (
      <div className="fixed inset-0 z-[1500] flex items-center justify-center bg-black/60" onClick={onClose}>
        <div className="bg-bg-secondary border border-border rounded-lg p-10 shadow-lg">
          <div className="animate-spin rounded-full h-10 w-10 border-2 border-accent border-t-transparent" />
        </div>
      </div>
    )
  }

  const set = (key: keyof PlaceCreate, value: string | number | null) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const mutation = isEdit ? updateMutation : createMutation
  const inputCls = 'bg-bg-card border border-border rounded px-2 py-1 text-sm text-text-primary w-full'
  const labelCls = 'text-xs text-text-secondary mb-1'

  return (
    <div className="fixed inset-0 z-[1500] flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-bg-secondary border border-border rounded-lg p-5 w-[90vw] max-w-2xl max-h-[85vh] overflow-y-auto shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-accent font-semibold">
            {isEdit ? `Edit Place — ${place?.name}` : 'New Place'}
          </h3>
          <button onClick={onClose} className="text-text-secondary hover:text-text-primary text-lg">
            &times;
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <div className="col-span-2">
            <div className={labelCls}>Name</div>
            <input
              className={inputCls}
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              placeholder="Place name"
            />
          </div>
          <div className="col-span-2">
            <div className={labelCls}>Place Type</div>
            <div className="flex items-center gap-2">
              <select
                className={inputCls}
                value={form.place_type_id}
                onChange={(e) => set('place_type_id', Number(e.target.value))}
              >
                {form.place_type_id === 0 && <option value={0}>— Select —</option>}
                {placeTypes?.items.map((pt) => (
                  <option key={pt.id} value={pt.id}>
                    {pt.name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => setShowTypes(true)}
                className="px-2 py-1 rounded border border-border text-xs text-text-secondary hover:text-text-primary transition-colors shrink-0"
              >
                Edit
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <div>
            <div className={labelCls}>Latitude</div>
            <input className={inputCls} value={form.lat} readOnly />
          </div>
          <div>
            <div className={labelCls}>Longitude</div>
            <input className={inputCls} value={form.lon} readOnly />
          </div>
          <div>
            <div className={labelCls}>Radius (m)</div>
            <input
              type="number"
              min="10"
              className={inputCls}
              value={form.distance_m ?? 200}
              onChange={(e) => set('distance_m', Number(e.target.value))}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-4">
          <div>
            <div className={labelCls}>Date From</div>
            <input
              type="date"
              className={inputCls}
              value={form.date_from ?? ''}
              onChange={(e) => set('date_from', e.target.value || null)}
            />
          </div>
          <div>
            <div className={labelCls}>Date To</div>
            <input
              type="date"
              className={inputCls}
              value={form.date_to ?? ''}
              onChange={(e) => set('date_to', e.target.value || null)}
            />
          </div>
        </div>

        <div className="mb-4">
          <div className={labelCls}>Notes</div>
          <textarea
            className={inputCls + ' h-20 resize-y'}
            value={form.notes ?? ''}
            onChange={(e) => set('notes', e.target.value || null)}
          />
        </div>

        <div className="flex gap-2 items-center">
          <button
            onClick={handleSave}
            disabled={mutation.isPending || syncing || !form.name || form.place_type_id === 0}
            className="px-4 py-1.5 rounded bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-50 transition-colors"
          >
            {mutation.isPending ? 'Saving...' : syncing ? 'Syncing...' : isEdit ? 'Save' : 'Create'}
          </button>
          {(saved || mutation.isSuccess) && (
            <span className="text-sm text-green-600">Saved &amp; synced</span>
          )}
          {mutation.isError && (
            <span className="text-sm text-red-600">{(mutation.error as Error).message}</span>
          )}

          {isEdit && (
            <div className="ml-auto">
              {confirmDelete ? (
                <div className="flex gap-2 items-center">
                  <span className="text-sm text-red-600">Delete this place?</span>
                  <button
                    onClick={() =>
                      deleteMutation.mutate(placeId, {
                        onSuccess: async () => {
                          await triggerJournalSync()
                          onClose()
                        },
                      })
                    }
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
          )}
        </div>
      </div>
      {showTypes && <PlaceTypesPanel onClose={() => setShowTypes(false)} />}
    </div>
  )
}
