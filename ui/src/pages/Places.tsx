import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { usePlaces, usePlaceLookup } from '../hooks/usePlaces'
import PlaceEditPanel from '../components/places/PlaceEditPanel'
import PlaceTypesPanel from '../components/places/PlaceTypesPanel'

const PER_PAGE = 25

export default function Places() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [showCreate, setShowCreate] = useState<{ name: string; lat: number; lon: number } | null>(null)
  const [showTypes, setShowTypes] = useState(false)

  const { data, isLoading, error } = usePlaces(page, PER_PAGE)

  // Query param support: ?lat=X&lon=Y&name=Z&dt=YYYY-MM-DD
  const paramLat = searchParams.get('lat') ? Number(searchParams.get('lat')) : null
  const paramLon = searchParams.get('lon') ? Number(searchParams.get('lon')) : null
  const paramName = searchParams.get('name') ?? ''
  const paramDt = searchParams.get('dt') ?? undefined

  const { data: lookupResult, isLoading: lookupLoading } = usePlaceLookup(paramLat, paramLon, paramDt)

  // Auto-open modal based on lookup result
  const [autoOpened, setAutoOpened] = useState(false)
  useEffect(() => {
    if (autoOpened || paramLat === null || paramLon === null) return
    if (lookupLoading) return

    if (lookupResult?.place) {
      setSelectedId(lookupResult.place.id)
    } else {
      setShowCreate({ name: paramName, lat: paramLat, lon: paramLon })
    }
    setAutoOpened(true)
  }, [lookupResult, lookupLoading, paramLat, paramLon, paramName, autoOpened])

  const handleClose = () => {
    setSelectedId(null)
    setShowCreate(null)
    // Clear query params after closing
    if (searchParams.has('lat')) {
      setSearchParams({})
    }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-bg-secondary border-b border-border">
        <h2 className="text-lg font-semibold text-text-primary">Places</h2>
        <div className="flex items-center gap-3">
          {data && (
            <span className="text-xs text-text-secondary">
              {data.total_count.toLocaleString()} places
            </span>
          )}
          <button
            onClick={() => setShowTypes(true)}
            className="px-3 py-1 rounded border border-border text-sm text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors"
          >
            Manage Types
          </button>
          <button
            onClick={() => setShowCreate({ name: '', lat: 0, lon: 0 })}
            className="px-3 py-1 rounded bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors"
          >
            New Place
          </button>
        </div>
      </div>

      {/* Loading for lookup */}
      {lookupLoading && paramLat !== null && (
        <div className="px-4 py-2 text-sm text-text-secondary bg-bg-secondary border-b border-border">
          Looking up place at {paramLat?.toFixed(4)}, {paramLon?.toFixed(4)}...
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {isLoading && (
          <div className="flex items-center justify-center h-40">
            <div className="animate-spin rounded-full h-10 w-10 border-2 border-accent border-t-transparent" />
          </div>
        )}

        {error && (
          <div className="m-4 bg-red-50 text-red-700 border border-red-200 px-4 py-2 rounded text-sm">
            {(error as Error).message}
          </div>
        )}

        {data && (
          <>
            <table className="w-full min-w-[700px]">
              <thead>
                <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wider">
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">Lat</th>
                  <th className="px-3 py-2">Lon</th>
                  <th className="px-3 py-2">Radius</th>
                  <th className="px-3 py-2">From</th>
                  <th className="px-3 py-2">To</th>
                  <th className="px-3 py-2">Notes</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((place) => (
                  <tr
                    key={place.id}
                    onClick={() => setSelectedId(place.id)}
                    className={`border-b border-border cursor-pointer transition-colors ${
                      selectedId === place.id
                        ? 'bg-accent/10'
                        : 'hover:bg-bg-hover'
                    }`}
                  >
                    <td className="px-3 py-2 text-sm font-medium text-text-primary">{place.name}</td>
                    <td className="px-3 py-2 text-sm text-text-secondary">{place.place_type_name}</td>
                    <td className="px-3 py-2 text-sm text-text-secondary tabular-nums">{place.lat.toFixed(4)}</td>
                    <td className="px-3 py-2 text-sm text-text-secondary tabular-nums">{place.lon.toFixed(4)}</td>
                    <td className="px-3 py-2 text-sm text-text-secondary">{place.distance_m}m</td>
                    <td className="px-3 py-2 text-sm text-text-secondary">{place.date_from ?? '—'}</td>
                    <td className="px-3 py-2 text-sm text-text-secondary">{place.date_to ?? '—'}</td>
                    <td className="px-3 py-2 text-sm text-text-secondary truncate max-w-[200px]">
                      {place.notes ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            {data.total_pages > 1 && (
              <div className="flex items-center justify-center gap-2 py-4 border-t border-border">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 rounded text-sm border border-border text-text-primary disabled:opacity-30 hover:bg-bg-hover transition-colors"
                >
                  Prev
                </button>

                {Array.from({ length: data.total_pages }, (_, i) => i + 1)
                  .filter((p) => p === 1 || p === data.total_pages || Math.abs(p - page) <= 2)
                  .reduce<(number | '...')[]>((acc, p, i, arr) => {
                    if (i > 0 && p - (arr[i - 1] as number) > 1) acc.push('...')
                    acc.push(p)
                    return acc
                  }, [])
                  .map((item, i) =>
                    item === '...' ? (
                      <span key={`gap-${i}`} className="px-1 text-text-secondary">...</span>
                    ) : (
                      <button
                        key={item}
                        onClick={() => setPage(item as number)}
                        className={`px-3 py-1 rounded text-sm transition-colors ${
                          page === item
                            ? 'bg-accent text-white font-medium'
                            : 'border border-border text-text-primary hover:bg-bg-hover'
                        }`}
                      >
                        {item}
                      </button>
                    ),
                  )}

                <button
                  onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                  disabled={page === data.total_pages}
                  className="px-3 py-1 rounded text-sm border border-border text-text-primary disabled:opacity-30 hover:bg-bg-hover transition-colors"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Edit modal */}
      {selectedId !== null && (
        <PlaceEditPanel placeId={selectedId} onClose={handleClose} />
      )}

      {/* Create modal */}
      {showCreate !== null && (
        <PlaceEditPanel placeId={null} onCreate={showCreate} onClose={handleClose} />
      )}

      {/* Place types modal */}
      {showTypes && <PlaceTypesPanel onClose={() => setShowTypes(false)} />}
    </div>
  )
}
