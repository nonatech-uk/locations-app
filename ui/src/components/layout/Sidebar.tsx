import { NavLink } from 'react-router-dom'

const links = [
  { to: '/explorer', label: 'Explorer' },
]

export default function Sidebar() {
  return (
    <aside className="w-48 shrink-0 bg-[var(--bg-secondary)] border-r border-white/10 flex flex-col">
      <div className="p-4 text-lg font-semibold text-[var(--accent)]">
        My Locations
      </div>
      <nav className="flex flex-col gap-1 px-2">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            className={({ isActive }) =>
              `px-3 py-2 rounded text-sm transition-colors ${
                isActive
                  ? 'bg-[var(--bg-surface)] text-[var(--accent)]'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-white/5'
              }`
            }
          >
            {l.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
