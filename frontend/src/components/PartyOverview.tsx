import { useEffect, useState } from 'react'
import { createPlayer, getPartyOverview, triggerCharacterSync } from '../api/resources'
import { CharacterSheet } from './CharacterSheet'
import type { PartyMemberPublic } from '../types/api'

export function PartyOverview({ token }: { token: string }) {
  const [party, setParty] = useState<PartyMemberPublic[]>([])
  const [error, setError] = useState<string | null>(null)
  const [syncing, setSyncing] = useState(false)

  const [username, setUsername] = useState('')
  const [discordId, setDiscordId] = useState('')
  const [characterId, setCharacterId] = useState('')
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    refresh()
  }, [])

  async function refresh() {
    try {
      setParty(await getPartyOverview(token))
      setError(null)
    } catch {
      setError('Could not load party overview.')
    }
  }

  async function handleSync() {
    setSyncing(true)
    try {
      await triggerCharacterSync(token)
      await refresh()
    } catch {
      setError('Sync failed.')
    } finally {
      setSyncing(false)
    }
  }

  async function handleAddPlayer(e: React.FormEvent) {
    e.preventDefault()
    if (!username.trim()) return
    setAdding(true)
    try {
      await createPlayer(token, {
        username: username.trim(),
        discord_id: discordId.trim() || null,
        dnd_beyond_character_id: characterId.trim() || null,
      })
      setUsername('')
      setDiscordId('')
      setCharacterId('')
      await refresh()
      if (characterId.trim()) await triggerCharacterSync(token).then(refresh)
    } catch {
      setError('Could not add player - is the username already taken?')
    } finally {
      setAdding(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-[var(--text)]">Party Overview</h3>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="rounded-md border border-[var(--border)] px-3 py-1.5 text-sm hover:bg-[var(--surface-2)] disabled:opacity-50"
        >
          {syncing ? 'Syncing...' : 'Sync from D&D Beyond'}
        </button>
      </div>
      <p className="-mt-2 text-xs text-[var(--text-faint)]">
        Optional: only reads characters you already have access to in your own D&D Beyond account.
        Lorekeeper is an independent app, not affiliated with or endorsed by D&D Beyond.
      </p>

      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

      <form onSubmit={handleAddPlayer} className="flex flex-wrap gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Player username"
          className="flex-1 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)] placeholder-[var(--text-faint)]"
        />
        <input
          value={discordId}
          onChange={(e) => setDiscordId(e.target.value)}
          placeholder="Discord user ID (optional)"
          className="flex-1 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)] placeholder-[var(--text-faint)]"
        />
        <input
          value={characterId}
          onChange={(e) => setCharacterId(e.target.value)}
          placeholder="D&D Beyond character ID (optional)"
          className="flex-1 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)] placeholder-[var(--text-faint)]"
        />
        <button
          type="submit"
          disabled={adding || !username.trim()}
          className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50"
        >
          Add player
        </button>
      </form>

      {party.length === 0 ? (
        <p className="text-sm text-[var(--text-faint)]">No players registered yet.</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {party.map((member) => (
            <div key={member.user_id} className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
              {member.character ? (
                <CharacterSheet character={member.character} />
              ) : (
                <div>
                  <h4 className="font-medium text-[var(--text)]">{member.username}</h4>
                  <p className="mt-1 text-sm text-[var(--text-faint)]">
                    {member.sync_error ?? 'No D&D Beyond character linked.'}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
