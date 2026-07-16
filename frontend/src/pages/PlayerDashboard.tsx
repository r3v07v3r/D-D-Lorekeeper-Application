import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { getActiveCampaign, getMyCharacter, listSessions } from '../api/resources'
import { CharacterSheet } from '../components/CharacterSheet'
import { CharacterIcon, SessionsIcon } from '../components/icons'
import { NotesPanel } from '../components/NotesPanel'
import { Sidebar, type SidebarNavItem } from '../components/Sidebar'
import type { CampaignPublic, CharacterPublic, SessionLogPublic } from '../types/api'

type Tab = 'character' | 'sessions'

const NAV_ITEMS: SidebarNavItem[] = [
  { key: 'character', label: 'My Character', icon: <CharacterIcon /> },
  { key: 'sessions', label: 'Session Recaps', icon: <SessionsIcon /> },
]

export function PlayerDashboard() {
  const { token, user } = useAuth()
  const [tab, setTab] = useState<Tab>('character')
  const [character, setCharacter] = useState<CharacterPublic | null>(null)
  const [characterError, setCharacterError] = useState<string | null>(null)
  const [sessions, setSessions] = useState<SessionLogPublic[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [campaign, setCampaign] = useState<CampaignPublic | null>(null)

  useEffect(() => {
    if (!token) return
    getMyCharacter(token)
      .then(setCharacter)
      .catch((err) => setCharacterError(err instanceof Error ? err.message : 'No character linked.'))
    listSessions(token).then((logs) => {
      setSessions(logs)
      if (logs.length > 0) setSelectedId(logs[logs.length - 1].id)
    })
    getActiveCampaign(token)
      .then(setCampaign)
      .catch(() => {})
  }, [token])

  if (!token || !user) return null

  const selected = sessions.find((s) => s.id === selectedId) ?? null

  return (
    <div className="space-y-3">
      {campaign && (
        <h2 className="text-sm font-medium text-[var(--text-muted)]">
          Campaign: <span className="text-[var(--text)]">{campaign.name}</span>
        </h2>
      )}

      <div className="flex gap-4">
        <Sidebar navItems={NAV_ITEMS} active={tab} onSelect={(key) => setTab(key as Tab)} />

        <div className="min-w-0 flex-1 space-y-4">
        {tab === 'character' && (
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
            {character ? (
              <CharacterSheet character={character} />
            ) : (
              <p className="text-sm text-[var(--text-faint)]">{characterError ?? 'Loading your character...'}</p>
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
                      selectedId === s.id ? 'bg-[var(--surface-2)] text-[var(--text)]' : 'text-[var(--text-muted)] hover:bg-[var(--surface)]'
                    }`}
                  >
                    <div className="font-medium">
                      {s.campaign_name} - Session {s.session_number}
                    </div>
                    <div className="text-xs text-[var(--text-faint)]">{s.date}</div>
                  </button>
                </li>
              ))}
              {sessions.length === 0 && <p className="text-sm text-[var(--text-faint)]">No sessions yet.</p>}
            </ul>

            <div className="lg:col-span-2">
              {selected ? (
                <div className="space-y-4 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
                  <h3 className="text-lg font-semibold text-[var(--text)]">
                    {selected.campaign_name} - Session {selected.session_number}
                  </h3>
                  <div>
                    <h4 className="mb-1 text-sm font-semibold uppercase tracking-wide text-[var(--text-faint)]">Recap</h4>
                    <p className="whitespace-pre-wrap text-sm text-[var(--text-muted)]">
                      {selected.player_summary ?? 'Not available yet - ask your GM to process this session.'}
                    </p>
                  </div>
                  <NotesPanel token={token} sessionId={selected.id} role="player" players={[]} />
                </div>
              ) : (
                <p className="text-sm text-[var(--text-faint)]">Select a session to see its recap.</p>
              )}
            </div>
          </div>
        )}
        </div>
      </div>
    </div>
  )
}
