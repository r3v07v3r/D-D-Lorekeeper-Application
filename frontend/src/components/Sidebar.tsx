import { useState, type ReactNode } from 'react'
import { CollapseIcon, ExpandIcon } from './icons'

export interface SidebarNavItem {
  key: string
  label: string
  icon: ReactNode
  badge?: number
}

const STORAGE_KEY = 'lorekeeper_sidebar_collapsed'

function loadCollapsed(): boolean {
  return localStorage.getItem(STORAGE_KEY) === '1'
}

// Icon-first navigation rail - not a primary content area, so it collapses
// to icon-only and stays out of the way once the GM/player knows where
// things are. Reused by both dashboards rather than each rolling its own nav.
export function Sidebar({
  navItems,
  active,
  onSelect,
  footer,
}: {
  navItems: SidebarNavItem[]
  active: string
  onSelect: (key: string) => void
  footer?: ReactNode
}) {
  const [collapsed, setCollapsed] = useState(loadCollapsed)

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev
      localStorage.setItem(STORAGE_KEY, next ? '1' : '0')
      return next
    })
  }

  return (
    <aside
      className={`flex shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface-2)] py-3 transition-[width] ${
        collapsed ? 'w-14 px-2' : 'w-52 px-3'
      }`}
    >
      <nav className="flex flex-1 flex-col gap-1">
        {navItems.map((item) => (
          <button
            key={item.key}
            onClick={() => onSelect(item.key)}
            title={collapsed ? item.label : undefined}
            className={`relative flex items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-sm font-medium ${
              active === item.key
                ? 'bg-[var(--surface)] text-[var(--text)] shadow-[inset_2px_0_0_var(--accent)]'
                : 'text-[var(--text-muted)] hover:bg-[var(--surface)] hover:text-[var(--text)]'
            }`}
          >
            {item.icon}
            {!collapsed && <span className="truncate">{item.label}</span>}
            {item.badge !== undefined && item.badge > 0 && (
              <span
                className={`flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--danger)] px-1 text-[10px] font-bold text-white ${
                  collapsed ? 'absolute -right-0.5 -top-0.5' : 'ml-auto'
                }`}
              >
                {item.badge}
              </span>
            )}
          </button>
        ))}
      </nav>

      {footer && <div className={collapsed ? 'hidden' : 'border-t border-[var(--border)] pt-3'}>{footer}</div>}

      <button
        onClick={toggleCollapsed}
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        className="mt-3 flex items-center justify-center rounded-md py-1.5 text-[var(--text-faint)] hover:bg-[var(--surface)] hover:text-[var(--text)]"
      >
        {collapsed ? <ExpandIcon /> : <CollapseIcon />}
      </button>
    </aside>
  )
}
