import type { ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-full bg-[var(--bg)] text-[var(--text)]">
      <header className="flex items-center justify-between border-b border-[var(--border)] px-6 py-3">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold">Lorekeeper</span>
          {user && (
            <span className="rounded-full bg-[var(--surface-2)] px-2 py-0.5 text-xs uppercase tracking-wide text-[var(--text-muted)]">
              {user.role}
            </span>
          )}
        </div>
        {user && (
          <div className="flex items-center gap-3 text-sm text-[var(--text-muted)]">
            <span>{user.username}</span>
            <button onClick={logout} className="rounded-md border border-[var(--border)] px-3 py-1 hover:bg-[var(--surface-2)]">
              Log out
            </button>
          </div>
        )}
      </header>
      <main className="mx-auto max-w-6xl px-6 py-6">{children}</main>
    </div>
  )
}
