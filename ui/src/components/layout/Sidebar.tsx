import { NavLink } from 'react-router-dom'

const links = [
  { to: '/explorer', label: 'Explorer' },
  { to: '/flights', label: 'Flights' },
  { to: '/ga', label: 'GA Flights' },
  { to: '/places', label: 'Places' },
]

export default function Sidebar() {
  return (
    <aside className="w-48 shrink-0 bg-bg-secondary border-r border-border flex flex-col">
      <div className="p-4 text-lg font-semibold text-accent">
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
                  ? 'bg-accent/15 text-accent font-medium'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
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
