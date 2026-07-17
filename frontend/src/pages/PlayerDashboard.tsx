import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { ApiError } from '../api/client'
import { getActiveCampaign, getMyCharacter, listSessions } from '../api/resources'
import { CharacterEditor } from '../components/CharacterEditor'
import { CharacterSheet } from '../components/CharacterSheet'
import { CharacterIcon, DiceIcon, SessionsIcon } from '../components/icons'
import { DiceRoller } from '../components/DiceRoller'
import { NotesPanel } from '../components/NotesPanel'
import { RollLog } from '../components/RollLog'
import { SessionHighlights } from '../components/SessionHighlights'
import { Sidebar, type SidebarNavItem } from '../components/Sidebar'
import { formatDuration } from '../utils/formatDuration'
import type { CampaignPublic, CharacterPublic, SessionLogPublic } from '../types/api'

type Tab = 'character' | 'dice' | 'sessions'

const NAV_ITEMS: SidebarNavItem[] = [
  { key: 'character', label: 'My Character', icon: <CharacterIcon /> },
  { key: 'dice', label: 'Dice Roller', icon: <DiceIcon /> },
  { key: 'sessions', label: 'Session Recaps', icon: <SessionsIcon /> },
]

export function PlayerDashboard() {
  const { token, user } = useAuth()
  const [tab, setTab] = useState<Tab>('character')
  // undefined = loading; null = confirmed no character yet (404); else the character.
  const [character, setCharacter] = useState<CharacterPublic | null | undefined>(undefined)
  const [characterError, setCharacterError] = useState<string | null>(null)
  const [editingCharacter, setEditingCharacter] = useState(false)
  const [sessions, setSessions] = useState<SessionLogPublic[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [campaign, setCampaign] = useState<CampaignPublic | null>(null)

  useEffect(() => {
    if (!token) return
    refreshCharacter()
    listSessions(token).then((logs) => {
      setSessions(logs)
      if (logs.length > 0) setSelectedId(logs[logs.length - 1].id)
    })
    getActiveCampaign(token)
      .then(setCampaign)
      .catch(() => {})
  }, [token])

  function refreshCharacter() {
    if (!token) return
    getMyCharacter(token)
      .then((c) => {
        setCharacter(c)
        setCharacterError(null)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          setCharacter(null)
        } else {
          setCharacterError(err instanceof Error ? err.message : 'Could not load your character.')
        }
      })
  }

  if (!token || !user) return null

  const selected = sessions.find((s) => s.id === selectedId) ?? null

  return (
    <div className="flex flex-1 flex-col space-y-3">
      <div className="flex items-center justify-between">
        {campaign && (
          <h2 className="text-sm font-medium text-[var(--text-muted)]">
            Campaign: <span className="text-[var(--text)]">{campaign.name}</span>
          </h2>
        )}
        <span className="text-xs text-[var(--text-faint)]">
          {formatDuration(user.total_seconds_active)} in Lorekeeper
        </span>
      </div>

      <div className="flex flex-1 gap-4">
        <Sidebar navItems={NAV_ITEMS} active={tab} onSelect={(key) => setTab(key as Tab)} />

        <div className="min-w-0 flex-1 space-y-4">
        {tab === 'character' && (
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
            {character === undefined ? (
              <p className="text-sm text-[var(--text-faint)]">Loading your character...</p>
            ) : characterError ? (
              <p className="text-sm text-[var(--danger)]">{characterError}</p>
            ) : character === null || editingCharacter ? (
              <CharacterEditor
                token={token}
                character={character}
                onSaved={(saved) => {
                  setCharacter(saved)
                  setEditingCharacter(false)
                }}
                onCancel={character ? () => setEditingCharacter(false) : undefined}
              />
            ) : (
              <div className="space-y-3">
                {character.source === 'manual' && (
                  <div className="flex justify-end">
                    <button
                      onClick={() => setEditingCharacter(true)}
                      className="text-xs text-[var(--accent)] hover:text-[var(--accent-hover)]"
                    >
                      Edit character
                    </button>
                  </div>
                )}
                <CharacterSheet character={character} editable token={token} onUpdated={setCharacter} />
              </div>
            )}
          </div>
        )}

        {tab === 'dice' && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <DiceRoller token={token} />
            </div>
            <RollLog token={token} />
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
                  <SessionHighlights highlights={selected.highlights} />
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
