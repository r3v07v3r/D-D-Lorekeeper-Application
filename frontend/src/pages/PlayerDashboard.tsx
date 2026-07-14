import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { getMyCharacter, listSessions } from '../api/resources'
import { CharacterSheet } from '../components/CharacterSheet'
import { NotesPanel } from '../components/NotesPanel'
import type { CharacterPublic, SessionLogPublic } from '../types/api'

type Tab = 'character' | 'sessions'

export function PlayerDashboard() {
  const { token, user } = useAuth()
  const [tab, setTab] = useState<Tab>('character')
  const [character, setCharacter] = useState<CharacterPublic | null>(null)
  const [characterError, setCharacterError] = useState<string | null>(null)
  const [sessions, setSessions] = useState<SessionLogPublic[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)

  useEffect(() => {
    if (!token) return
    getMyCharacter(token)
      .then(setCharacter)
      .catch((err) => setCharacterError(err instanceof Error ? err.message : 'No character linked.'))
    listSessions(token).then((logs) => {
      setSessions(logs)
      if (logs.length > 0) setSelectedId(logs[logs.length - 1].id)
    })
  }, [token])

  if (!token || !user) return null

  const selected = sessions.find((s) => s.id === selectedId) ?? null

  return (
    <div className="space-y-4">
      <nav className="flex gap-2 border-b border-slate-800">
        {(['character', 'sessions'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm font-medium capitalize ${
              tab === t ? 'border-b-2 border-indigo-500 text-slate-100' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {t === 'character' ? 'My Character' : 'Session Recaps'}
          </button>
        ))}
      </nav>

      {tab === 'character' && (
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          {character ? (
            <CharacterSheet character={character} />
          ) : (
            <p className="text-sm text-slate-500">{characterError ?? 'Loading your character...'}</p>
          )}
        </div>
      )}

      {tab === 'sessions' && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <ul className="space-y-1 lg:col-span-1">
            {sessions.map((s) => (
              <li key={s.id}>
                <button
                  onClick={() => setSelectedId(s.id)}
                  className={`w-full rounded-md px-3 py-2 text-left text-sm ${
                    selectedId === s.id ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:bg-slate-900'
                  }`}
                >
                  <div className="font-medium">
                    {s.campaign_name} - Session {s.session_number}
                  </div>
                  <div className="text-xs text-slate-500">{s.date}</div>
                </button>
              </li>
            ))}
            {sessions.length === 0 && <p className="text-sm text-slate-500">No sessions yet.</p>}
          </ul>

          <div className="lg:col-span-2">
            {selected ? (
              <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900 p-4">
                <h3 className="text-lg font-semibold text-slate-100">
                  {selected.campaign_name} - Session {selected.session_number}
                </h3>
                <div>
                  <h4 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500">Recap</h4>
                  <p className="whitespace-pre-wrap text-sm text-slate-300">
                    {selected.player_summary ?? 'Not available yet - ask your GM to process this session.'}
                  </p>
                </div>
                <NotesPanel token={token} sessionId={selected.id} role="player" players={[]} />
              </div>
            ) : (
              <p className="text-sm text-slate-500">Select a session to see its recap.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
