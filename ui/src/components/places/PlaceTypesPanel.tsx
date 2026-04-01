import { useState } from 'react'
import { usePlaceTypes, useCreatePlaceType, useUpdatePlaceType, useDeletePlaceType } from '../../hooks/usePlaces'

interface Props {
  onClose: () => void
}

export default function PlaceTypesPanel({ onClose }: Props) {
  const { data: placeTypes, isLoading } = usePlaceTypes()
  const createMutation = useCreatePlaceType()
  const updateMutation = useUpdatePlaceType()
  const deleteMutation = useDeletePlaceType()

  const [newName, setNewName] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleCreate = () => {
    if (!newName.trim()) return
    setError(null)
    createMutation.mutate(newName.trim(), {
      onSuccess: () => setNewName(''),
      onError: (e) => setError((e as Error).message),
    })
  }

  const handleUpdate = (id: number) => {
    if (!editName.trim()) return
    setError(null)
    updateMutation.mutate(
      { id, name: editName.trim() },
      {
        onSuccess: () => setEditingId(null),
        onError: (e) => setError((e as Error).message),
      },
    )
  }

  const handleDelete = (id: number) => {
    setError(null)
    deleteMutation.mutate(id, {
      onSuccess: () => setConfirmDeleteId(null),
      onError: (e) => {
        setError((e as Error).message)
        setConfirmDeleteId(null)
      },
    })
  }

  const inputCls = 'bg-bg-card border border-border rounded px-2 py-1 text-sm text-text-primary w-full'

  return (
    <div className="fixed inset-0 z-[1500] flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-bg-secondary border border-border rounded-lg p-5 w-[90vw] max-w-md max-h-[85vh] overflow-y-auto shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-accent font-semibold">Place Types</h3>
          <button onClick={onClose} className="text-text-secondary hover:text-text-primary text-lg">
            &times;
          </button>
        </div>

        {error && (
          <div className="mb-3 bg-red-50 text-red-700 border border-red-200 px-3 py-1.5 rounded text-sm">
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center h-20">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-accent border-t-transparent" />
          </div>
        ) : (
          <div className="space-y-2 mb-4">
            {placeTypes?.items.map((pt) => (
              <div key={pt.id} className="flex items-center gap-2">
                {editingId === pt.id ? (
                  <>
                    <input
                      className={inputCls}
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleUpdate(pt.id)}
                      autoFocus
                    />
                    <button
                      onClick={() => handleUpdate(pt.id)}
                      disabled={updateMutation.isPending}
                      className="px-2 py-1 rounded bg-accent text-white text-xs font-medium hover:bg-accent-hover disabled:opacity-50 transition-colors shrink-0"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="px-2 py-1 rounded border border-border text-xs text-text-secondary hover:text-text-primary transition-colors shrink-0"
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <span className="text-sm text-text-primary flex-1">{pt.name}</span>
                    <button
                      onClick={() => {
                        setEditingId(pt.id)
                        setEditName(pt.name)
                      }}
                      className="px-2 py-1 rounded border border-border text-xs text-text-secondary hover:text-text-primary transition-colors shrink-0"
                    >
                      Edit
                    </button>
                    {confirmDeleteId === pt.id ? (
                      <div className="flex gap-1 shrink-0">
                        <button
                          onClick={() => handleDelete(pt.id)}
                          disabled={deleteMutation.isPending}
                          className="px-2 py-1 rounded bg-red-600 text-white text-xs font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
                        >
                          Confirm
                        </button>
                        <button
                          onClick={() => setConfirmDeleteId(null)}
                          className="px-2 py-1 rounded border border-border text-xs text-text-secondary hover:text-text-primary transition-colors"
                        >
                          No
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirmDeleteId(pt.id)}
                        className="px-2 py-1 rounded border border-red-300 text-xs text-red-600 hover:bg-red-50 transition-colors shrink-0"
                      >
                        Delete
                      </button>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Add new */}
        <div className="flex items-center gap-2 pt-3 border-t border-border">
          <input
            className={inputCls}
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            placeholder="New type name..."
          />
          <button
            onClick={handleCreate}
            disabled={createMutation.isPending || !newName.trim()}
            className="px-3 py-1 rounded bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-50 transition-colors shrink-0"
          >
            Add
          </button>
        </div>
      </div>
    </div>
  )
}
