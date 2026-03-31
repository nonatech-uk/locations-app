import { useState } from 'react'
import { useGAFlights } from '../hooks/useGAFlights'
import GAFlightRow from '../components/ga/GAFlightRow'
import GAFlightEditPanel from '../components/ga/GAFlightEditPanel'

const PER_PAGE = 25

export default function GAFlights() {
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const { data, isLoading, error } = useGAFlights(page, PER_PAGE)

  const handleSelect = (id: number) => {
    setSelectedId((prev) => (prev === id ? null : id))
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 bg-bg-secondary border-b border-border">
        <h2 className="text-lg font-semibold text-text-primary">GA Flights</h2>
        {data && (
          <span className="text-xs text-text-secondary">
            {data.total_count.toLocaleString()} flights
          </span>
        )}
      </div>

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
            <table className="w-full">
              <thead>
                <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wider">
                  <th className="px-3 py-2">Date</th>
                  <th className="px-3 py-2">Route</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">Reg</th>
                  <th className="px-3 py-2">Captain</th>
                  <th className="px-3 py-2 text-center">Capacity</th>
                  <th className="px-3 py-2 text-right">Hours</th>
                  <th className="px-3 py-2">Exercise</th>
                  <th className="px-2 py-2">Route</th>
                  <th className="px-2 py-2">Aircraft</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((flight) => (
                  <GAFlightRow
                    key={flight.id}
                    flight={flight}
                    isSelected={selectedId === flight.id}
                    onSelect={() => handleSelect(flight.id)}
                  />
                ))}
              </tbody>
            </table>

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

      {selectedId !== null && (
        <GAFlightEditPanel
          flightId={selectedId}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  )
}
