import { NavLink } from 'react-router-dom'
import AppSwitcher from './AppSwitcher'

const links = [
  { to: '/explorer', label: 'Explorer' },
  { to: '/places', label: 'Places' },
]

export default function TopNav() {
  return (
    <header className="h-12 shrink-0 bg-bg-secondary border-b border-border flex items-center px-4 gap-6">
      <div className="flex items-center gap-2 mr-4">
        <span className="text-lg font-semibold text-accent">My Locations</span>
        <AppSwitcher />
      </div>
      <nav className="flex gap-1">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            className={({ isActive }) =>
              `px-3 py-1.5 rounded text-sm transition-colors ${
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
    </header>
  )
}
