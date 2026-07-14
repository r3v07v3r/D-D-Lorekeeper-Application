import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { UserPublic } from '../types/api'

export function LoginPage() {
  const { loginAs } = useAuth()
  const [users, setUsers] = useState<UserPublic[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busyUserId, setBusyUserId] = useState<number | null>(null)

  // First-run bootstrap: no users registered yet.
  const [newUsername, setNewUsername] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    refreshUsers()
  }, [])

  async function refreshUsers() {
    setLoading(true)
    try {
      setUsers(await api.get<UserPublic[]>('/users'))
      setError(null)
    } catch {
      setError('Could not reach the Lorekeeper backend. Is it running?')
    } finally {
      setLoading(false)
    }
  }

  async function handleSelect(user: UserPublic) {
    setBusyUserId(user.id)
    try {
      await loginAs(user.id)
    } catch {
      setError(`Could not log in as ${user.username}.`)
    } finally {
      setBusyUserId(null)
    }
  }

  async function handleBootstrapGm(e: React.FormEvent) {
    e.preventDefault()
    if (!newUsername.trim()) return
    setCreating(true)
    try {
      const created = await api.post<UserPublic>('/users', { username: newUsername.trim(), role: 'gm' })
      setNewUsername('')
      await loginAs(created.id)
    } catch {
      setError('Could not create the GM profile.')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-8 shadow-xl">
        <h1 className="mb-1 text-2xl font-semibold text-slate-100">Lorekeeper</h1>
        <p className="mb-6 text-sm text-slate-400">Choose your profile to continue.</p>

        {error && (
          <div className="mb-4 rounded-md border border-red-800 bg-red-950 px-3 py-2 text-sm text-red-300">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-sm text-slate-500">Loading profiles...</p>
        ) : users.length > 0 ? (
          <ul className="space-y-2">
            {users.map((user) => (
              <li key={user.id}>
                <button
                  onClick={() => handleSelect(user)}
                  disabled={busyUserId !== null}
                  className="flex w-full items-center justify-between rounded-lg border border-slate-800 bg-slate-800/50 px-4 py-3 text-left transition hover:border-indigo-500 hover:bg-slate-800 disabled:opacity-50"
                >
                  <span className="font-medium text-slate-100">{user.username}</span>
                  <span className="rounded-full bg-slate-700 px-2 py-0.5 text-xs uppercase tracking-wide text-slate-300">
                    {user.role}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <form onSubmit={handleBootstrapGm} className="space-y-3">
            <p className="text-sm text-slate-400">
              No profiles exist yet. Create the first one - it becomes the GM.
            </p>
            <input
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              placeholder="GM username"
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={creating || !newUsername.trim()}
              className="w-full rounded-md bg-indigo-600 px-3 py-2 font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
            >
              {creating ? 'Creating...' : 'Create GM profile'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
