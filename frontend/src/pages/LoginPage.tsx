import { useEffect, useState } from 'react'
import { api, ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { ServerConnect } from '../components/ServerConnect'
import { getServerConfig, setServerConfig } from '../api/serverConfig'
import type { UserPublic } from '../types/api'

export function LoginPage() {
  const { loginAs } = useAuth()
  const [users, setUsers] = useState<UserPublic[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busyUserId, setBusyUserId] = useState<number | null>(null)
  // True when the last attempt failed specifically because a campaign
  // passphrase is required - shows a field to enter it right here, rather
  // than only inside the "Joining someone else's game" panel. This is also
  // the only way to unlock "This computer" once its own GM has set a
  // passphrase (see backend/app/auth.py:require_network_access - once one
  // is set, it's required even from the GM's own machine).
  const [needsPassphrase, setNeedsPassphrase] = useState(false)
  const [passphraseInput, setPassphraseInput] = useState('')
  const [submittingPassphrase, setSubmittingPassphrase] = useState(false)

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
      setNeedsPassphrase(false)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError('Wrong campaign passphrase - check with your GM and try again.')
        setNeedsPassphrase(true)
      } else if (err instanceof ApiError && err.status === 403) {
        setError("This server isn't accepting remote connections yet - the GM needs to set a campaign passphrase in Settings first.")
        setNeedsPassphrase(false)
      } else {
        setError('Could not reach that server. Check the address and that it is running.')
        setNeedsPassphrase(false)
      }
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmitPassphrase(e: React.FormEvent) {
    e.preventDefault()
    if (!passphraseInput.trim()) return
    setSubmittingPassphrase(true)
    setServerConfig({ ...getServerConfig(), passphrase: passphraseInput.trim() })
    await refreshUsers()
    setSubmittingPassphrase(false)
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
    <div className="flex min-h-full items-center justify-center bg-[var(--bg)] px-4">
      <div className="w-full max-w-md rounded-xl border border-[var(--border)] bg-[var(--surface)] p-8 shadow-xl">
        <h1 className="mb-1 text-2xl font-semibold text-[var(--text)]">Lorekeeper</h1>
        <p className="mb-4 text-sm text-[var(--text-muted)]">Choose your profile to continue.</p>

        <ServerConnect onChanged={refreshUsers} />

        {error && (
          <div className="mb-4 rounded-md border border-[var(--danger)] bg-[var(--danger-soft)] px-3 py-2 text-sm text-[var(--danger)]">
            {error}
          </div>
        )}

        {needsPassphrase && (
          <form onSubmit={handleSubmitPassphrase} className="mb-4 space-y-2">
            <input
              type="password"
              value={passphraseInput}
              onChange={(e) => setPassphraseInput(e.target.value)}
              placeholder="Campaign passphrase"
              autoFocus
              className="w-full rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-[var(--text)] placeholder-[var(--text-faint)] focus:border-[var(--accent)] focus:outline-none"
            />
            <button
              type="submit"
              disabled={submittingPassphrase || !passphraseInput.trim()}
              className="w-full rounded-md bg-[var(--accent)] px-3 py-2 font-medium text-white transition hover:bg-[var(--accent-hover)] disabled:opacity-50"
            >
              {submittingPassphrase ? 'Checking...' : 'Continue'}
            </button>
          </form>
        )}

        {loading ? (
          <p className="text-sm text-[var(--text-faint)]">Loading profiles...</p>
        ) : error ? null : users.length > 0 ? (
          <ul className="space-y-2">
            {users.map((user) => (
              <li key={user.id}>
                <button
                  onClick={() => handleSelect(user)}
                  disabled={busyUserId !== null}
                  className="flex w-full items-center justify-between rounded-lg border border-[var(--border)] bg-[var(--surface-2)]/50 px-4 py-3 text-left transition hover:border-[var(--accent)] hover:bg-[var(--surface-2)] disabled:opacity-50"
                >
                  <span className="font-medium text-[var(--text)]">{user.username}</span>
                  <span className="rounded-full bg-[var(--surface-2)] px-2 py-0.5 text-xs uppercase tracking-wide text-[var(--text-muted)]">
                    {user.role}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <form onSubmit={handleBootstrapGm} className="space-y-3">
            <p className="text-sm text-[var(--text-muted)]">
              No profiles exist yet. Create the first one - it becomes the GM.
            </p>
            <input
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              placeholder="GM username"
              className="w-full rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-[var(--text)] placeholder-[var(--text-faint)] focus:border-[var(--accent)] focus:outline-none"
            />
            <button
              type="submit"
              disabled={creating || !newUsername.trim()}
              className="w-full rounded-md bg-[var(--accent)] px-3 py-2 font-medium text-white transition hover:bg-[var(--accent-hover)] disabled:opacity-50"
            >
              {creating ? 'Creating...' : 'Create GM profile'}
            </button>
            <p className="text-xs text-[var(--text-faint)]">
              After logging in, add your players from the Party tab. They can join from their own
              computer using "Joining someone else's game?" above.
            </p>
          </form>
        )}
      </div>
    </div>
  )
}
