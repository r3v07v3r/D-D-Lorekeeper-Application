import type { ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()

  return (
    // flex-col + main's flex-1 below is what actually makes the page fill
    // the window: min-h-full alone only sets a *minimum* on this div itself,
    // it doesn't give <main> (or anything inside it, like the sidebar) a
    // real height to stretch to - on a tab with little content (e.g. Party
    // with just one player), everything before this fix just collapsed to
    // its own content height, leaving a bare, uncolored gap below/beside it
    // that looked like the page wasn't filling the window.
    <div className="flex min-h-full flex-col bg-[var(--bg)] text-[var(--text)]">
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
      {/* flex flex-col here (not just flex-1) so children can use flex-1
          themselves to fill this space - percentage heights (h-full) on a
          padded flex item don't reliably resolve against its content box
          across engines; a flex-grow chain doesn't have that ambiguity. */}
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-6 py-6">{children}</main>
    </div>
  )
}
