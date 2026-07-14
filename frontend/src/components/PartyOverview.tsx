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
        <h3 className="text-lg font-semibold text-slate-100">Party Overview</h3>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="rounded-md border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-800 disabled:opacity-50"
        >
          {syncing ? 'Syncing...' : 'Sync from D&D Beyond'}
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <form onSubmit={handleAddPlayer} className="flex flex-wrap gap-2 rounded-lg border border-slate-800 bg-slate-900 p-3">
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Player username"
          className="flex-1 rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500"
        />
        <input
          value={discordId}
          onChange={(e) => setDiscordId(e.target.value)}
          placeholder="Discord user ID (optional)"
          className="flex-1 rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500"
        />
        <input
          value={characterId}
          onChange={(e) => setCharacterId(e.target.value)}
          placeholder="D&D Beyond character ID (optional)"
          className="flex-1 rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500"
        />
        <button
          type="submit"
          disabled={adding || !username.trim()}
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          Add player
        </button>
      </form>

      {party.length === 0 ? (
        <p className="text-sm text-slate-500">No players registered yet.</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {party.map((member) => (
            <div key={member.user_id} className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              {member.character ? (
                <CharacterSheet character={member.character} />
              ) : (
                <div>
                  <h4 className="font-medium text-slate-100">{member.username}</h4>
                  <p className="mt-1 text-sm text-slate-500">
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
