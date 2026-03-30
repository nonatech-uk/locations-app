import { useState } from 'react'
import { useFlights } from '../hooks/useFlights'
import FlightRow from '../components/flights/FlightRow'
import FlightEditPanel from '../components/flights/FlightEditPanel'

const PER_PAGE = 25

export default function Flights() {
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const { data, isLoading, error } = useFlights(page, PER_PAGE)

  const handleSelect = (id: number) => {
    setSelectedId((prev) => (prev === id ? null : id))
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-[var(--bg-secondary)] border-b border-white/10">
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">Flights</h2>
        {data && (
          <span className="text-xs text-[var(--text-secondary)]">
            {data.total_count.toLocaleString()} flights
          </span>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {isLoading && (
          <div className="flex items-center justify-center h-40">
            <div className="animate-spin rounded-full h-10 w-10 border-2 border-[var(--accent)] border-t-transparent" />
          </div>
        )}

        {error && (
          <div className="m-4 bg-red-900/80 text-red-200 px-4 py-2 rounded text-sm">
            {(error as Error).message}
          </div>
        )}

        {data && (
          <>
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10 text-left text-xs text-[var(--text-secondary)] uppercase tracking-wider">
                  <th className="px-3 py-2">Date</th>
                  <th className="px-3 py-2">Route</th>
                  <th className="px-3 py-2">Flight</th>
                  <th className="px-3 py-2">Airline</th>
                  <th className="px-3 py-2">Aircraft</th>
                  <th className="px-3 py-2">Duration</th>
                  <th className="px-3 py-2 text-center">Class</th>
                  <th className="px-3 py-2">Notes</th>
                  <th className="px-2 py-2">Route</th>
                  <th className="px-2 py-2">Aircraft</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((flight) => (
                  <FlightRow
                    key={flight.id}
                    flight={flight}
                    isSelected={selectedId === flight.id}
                    onSelect={() => handleSelect(flight.id)}
                  />
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            {data.total_pages > 1 && (
              <div className="flex items-center justify-center gap-2 py-4 border-t border-white/10">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 rounded text-sm bg-[var(--bg-surface)] text-[var(--text-primary)] disabled:opacity-30 hover:bg-white/10 transition-colors"
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
                      <span key={`gap-${i}`} className="px-1 text-[var(--text-secondary)]">...</span>
                    ) : (
                      <button
                        key={item}
                        onClick={() => setPage(item as number)}
                        className={`px-3 py-1 rounded text-sm transition-colors ${
                          page === item
                            ? 'bg-[var(--accent)] text-black font-medium'
                            : 'bg-[var(--bg-surface)] text-[var(--text-primary)] hover:bg-white/10'
                        }`}
                      >
                        {item}
                      </button>
                    ),
                  )}

                <button
                  onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                  disabled={page === data.total_pages}
                  className="px-3 py-1 rounded text-sm bg-[var(--bg-surface)] text-[var(--text-primary)] disabled:opacity-30 hover:bg-white/10 transition-colors"
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
        <FlightEditPanel
          flightId={selectedId}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  )
}
