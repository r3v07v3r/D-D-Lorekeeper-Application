import type { ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-full bg-slate-950 text-slate-100">
      <header className="flex items-center justify-between border-b border-slate-800 px-6 py-3">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold">Lorekeeper</span>
          {user && (
            <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs uppercase tracking-wide text-slate-400">
              {user.role}
            </span>
          )}
        </div>
        {user && (
          <div className="flex items-center gap-3 text-sm text-slate-400">
            <span>{user.username}</span>
            <button onClick={logout} className="rounded-md border border-slate-700 px-3 py-1 hover:bg-slate-800">
              Log out
            </button>
          </div>
        )}
      </header>
      <main className="mx-auto max-w-6xl px-6 py-6">{children}</main>
    </div>
  )
}
