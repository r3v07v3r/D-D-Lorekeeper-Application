import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import {
  createSession,
  getActiveCampaign,
  getPartyOverview,
  getSettings,
  getUserPresence,
  listSessions,
  listUsers,
  processSession,
} from '../api/resources'
import { CampaignPicker } from '../components/CampaignPicker'
import { NotesPanel } from '../components/NotesPanel'
import { BotControlPanel } from '../components/BotControlPanel'
import { PartyOverview } from '../components/PartyOverview'
import { Sidebar, type SidebarNavItem } from '../components/Sidebar'
import { HomeIcon, LiveIcon, PartyIcon, SessionsIcon, SettingsIcon } from '../components/icons'
import { SettingsPanel } from '../components/SettingsPanel'
import { SetupBanner } from '../components/SetupBanner'
import { SoundboardPanel } from '../components/SoundboardPanel'
import type { CampaignPublic, PartyMemberPublic, SessionLogPublic, SetupItem, UserPublic } from '../types/api'

type Tab = 'home' | 'sessions' | 'party' | 'bot' | 'soundboard' | 'settings'

export function GMDashboard() {
  const { token } = useAuth()
  const [tab, setTab] = useState<Tab>('home')
  const [sessions, setSessions] = useState<SessionLogPublic[]>([])
  const [players, setPlayers] = useState<UserPublic[]>([])
  const [party, setParty] = useState<PartyMemberPublic[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [setupItems, setSetupItems] = useState<SetupItem[]>([])
  const [botConfigured, setBotConfigured] = useState(false)
  const [focusSettingsKey, setFocusSettingsKey] = useState<string | null>(null)
  const [presence, setPresence] = useState<Record<string, boolean>>({})

  // undefined = still loading; null = loaded, nothing active yet (shows the
  // picker); a CampaignPublic once one is selected.
  const [activeCampaign, setActiveCampaignState] = useState<CampaignPublic | null | undefined>(undefined)
  const [switchingCampaign, setSwitchingCampaign] = useState(false)

  const [sessionNumber, setSessionNumber] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    if (!token) return
    getActiveCampaign(token)
      .then(setActiveCampaignState)
      .catch(() => setActiveCampaignState(null))
  }, [token])

  useEffect(() => {
    if (!token) return
    refreshSessions()
    listUsers()
      .then((all) => setPlayers(all.filter((u) => u.role === 'player')))
      .catch(() => {})
    getPartyOverview(token)
      .then(setParty)
      .catch(() => {})
  }, [token, activeCampaign])

  useEffect(() => {
    if (!token) return
    // On mount + a periodic interval, not on every tab change - refetching
    // this on every single navigation click (regardless of whether Settings
    // was even involved) made ordinary tab switching feel slow, since this
    // call can carry a real network cost server-side (Ollama reachability,
    // public IP detection). Guarded against a superseded request resolving
    // after a newer one and clobbering fresher data with stale data.
    let cancelled = false
    function refresh() {
      getSettings(token as string)
        .then((s) => {
          if (!cancelled) {
            setSetupItems(s.setup_items)
            setBotConfigured(s.discord_bot_token_set)
          }
        })
        .catch(() => {})
    }
    refresh()
    const interval = setInterval(refresh, 30_000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [token])

  useEffect(() => {
    if (!token) return
    // Polled at the same 5s cadence BotControlPanel already uses for its own
    // status - this is an in-memory, no-I/O lookup server-side (see
    // SessionStore.connected_user_ids), so frequent polling costs nothing.
    let cancelled = false
    function refresh() {
      getUserPresence(token as string)
        .then((p) => {
          if (!cancelled) setPresence(p)
        })
        .catch(() => {})
    }
    refresh()
    const interval = setInterval(refresh, 5_000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [token])

  async function refreshSessions() {
    if (!token) return
    try {
      const logs = await listSessions(token)
      setSessions(logs)
      if (selectedId === null && logs.length > 0) setSelectedId(logs[logs.length - 1].id)
      setError(null)
    } catch {
      setError('Could not load sessions.')
    }
  }

  async function handleCreateSession(e: React.FormEvent) {
    e.preventDefault()
    if (!token || !sessionNumber) return
    setCreating(true)
    try {
      const log = await createSession(token, {
        session_number: Number(sessionNumber),
        date: new Date().toISOString().slice(0, 10),
      })
      setSessionNumber('')
      await refreshSessions()
      setSelectedId(log.id)
    } catch {
      setError('Could not create session.')
    } finally {
      setCreating(false)
    }
  }

  async function handleProcess(id: number) {
    if (!token) return
    try {
      await processSession(token, id)
      await refreshSessions()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start processing.')
    }
  }

  // SettingsPanel fetches its own data asynchronously before rendering the
  // actual form fields, so the "setup-<key>" anchor a banner item points at
  // doesn't exist in the DOM the instant we switch tabs - retries briefly
  // rather than assuming a single frame/timeout is enough. focusSettingsKey
  // additionally tells SettingsPanel which of its own sub-tabs to switch to,
  // since the anchor may live in a section that isn't currently selected.
  function goToSettings(key?: string) {
    setTab('settings')
    setFocusSettingsKey(key ?? null)
    if (!key) return
    let attempts = 0
    const tryScroll = () => {
      const el = document.getElementById(`setup-${key}`)
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        el.classList.add('ring-2', 'ring-[var(--accent)]', 'rounded-md')
        setTimeout(() => el.classList.remove('ring-2', 'ring-[var(--accent)]', 'rounded-md'), 2000)
        return
      }
      attempts += 1
      if (attempts < 20) setTimeout(tryScroll, 100)
    }
    setTimeout(tryScroll, 50)
  }

  if (!token) return null

  if (activeCampaign === undefined) {
    return <p className="text-sm text-[var(--text-faint)]">Loading...</p>
  }

  if (activeCampaign === null || switchingCampaign) {
    return (
      <CampaignPicker
        token={token}
        onSelected={(campaign) => {
          setActiveCampaignState(campaign)
          setSwitchingCampaign(false)
          setSelectedId(null)
          setTab('home')
        }}
        onCancel={activeCampaign ? () => setSwitchingCampaign(false) : undefined}
      />
    )
  }

  const selected = sessions.find((s) => s.id === selectedId) ?? null

  const requiredSetupCount = setupItems.filter((i) => i.severity === 'required').length

  const navItems: SidebarNavItem[] = [
    { key: 'home', label: 'Home', icon: <HomeIcon /> },
    { key: 'sessions', label: 'Sessions', icon: <SessionsIcon /> },
    { key: 'party', label: 'Party', icon: <PartyIcon /> },
    { key: 'bot', label: 'Bot Control', icon: <LiveIcon /> },
    { key: 'soundboard', label: 'Soundboard', icon: <LiveIcon /> },
    { key: 'settings', label: 'Settings', icon: <SettingsIcon />, badge: requiredSetupCount },
  ]

  const partyFooter = players.length > 0 && (
    <div>
      <div className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-[var(--text-faint)]">
        Party
      </div>
      <ul className="space-y-1">
        {players.map((p) => {
          const online = presence[String(p.id)] === true
          return (
            <li key={p.id} className="flex items-center gap-2 text-xs" title={online ? 'Connected' : 'Offline'}>
              <span
                className={`h-2 w-2 shrink-0 rounded-full ${online ? 'bg-[var(--success)]' : 'bg-[var(--text-faint)]'}`}
              />
              <span className={online ? 'text-[var(--text)]' : 'text-[var(--text-faint)]'}>{p.username}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-[var(--text-muted)]">
          Campaign: <span className="text-[var(--text)]">{activeCampaign.name}</span>
        </h2>
        <button
          type="button"
          onClick={() => setSwitchingCampaign(true)}
          className="text-xs text-[var(--accent)] hover:text-[var(--accent-hover)]"
        >
          Switch campaign
        </button>
      </div>

      <div className="flex gap-4">
        <Sidebar navItems={navItems} active={tab} onSelect={(key) => setTab(key as Tab)} footer={partyFooter || undefined} />

        <div className="min-w-0 flex-1 space-y-4">
        {tab === 'home' && <SetupBanner items={setupItems} onGoToSettings={goToSettings} />}

        {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

        {tab === 'home' && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="space-y-4 lg:col-span-2">
              {(() => {
                const lastComplete = [...sessions].reverse().find((s) => s.processing_status === 'complete')
                return lastComplete ? (
                  <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
                    <h4 className="mb-2 text-sm font-semibold text-[var(--text)]">
                      Continue the story <span className="font-normal text-[var(--text-faint)]">- Session {lastComplete.session_number}</span>
                    </h4>
                    <p className="mb-3 whitespace-pre-wrap text-sm text-[var(--text-muted)]">
                      {lastComplete.player_summary ?? lastComplete.gm_summary}
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedId(lastComplete.id)
                        setTab('sessions')
                      }}
                      className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
                    >
                      Open Session {lastComplete.session_number}
                    </button>
                  </div>
                ) : (
                  <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
                    <h4 className="mb-1 text-sm font-semibold text-[var(--text)]">Continue the story</h4>
                    <p className="text-sm text-[var(--text-faint)]">
                      No processed sessions yet - transcribe a session to see its recap here.
                    </p>
                  </div>
                )
              })()}

              <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
                <h4 className="mb-2 text-sm font-semibold text-[var(--text)]">Quick actions</h4>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setTab('sessions')}
                    className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
                  >
                    Go to Sessions
                  </button>
                  <button
                    type="button"
                    onClick={() => setTab('bot')}
                    className="rounded-md border border-[var(--border)] px-3 py-1.5 text-sm hover:bg-[var(--surface-2)]"
                  >
                    Bot Control
                  </button>
                  <button
                    type="button"
                    onClick={() => setTab('soundboard')}
                    className="rounded-md border border-[var(--border)] px-3 py-1.5 text-sm hover:bg-[var(--surface-2)]"
                  >
                    Open Soundboard
                  </button>
                  {window.lorekeeper && botConfigured && (
                    <button
                      type="button"
                      onClick={() => window.lorekeeper?.openBotPanel()}
                      title="Opens Bot Control + Soundboard in their own window, e.g. to keep on a second monitor"
                      className="rounded-md border border-[var(--border)] px-3 py-1.5 text-sm hover:bg-[var(--surface-2)]"
                    >
                      Detach Bot Control window
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
              <h4 className="mb-3 text-sm font-semibold text-[var(--text)]">Party glance</h4>
              {party.length === 0 ? (
                <p className="text-sm text-[var(--text-faint)]">No players registered yet.</p>
              ) : (
                <ul className="space-y-2">
                  {party.map((member) => {
                    const c = member.character
                    const hpPct = c ? Math.max(0, Math.min(100, (c.hp_current / Math.max(c.hp_max, 1)) * 100)) : null
                    return (
                      <li key={member.user_id} className="text-sm">
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-[var(--text)]">{member.username}</span>
                          {c && (
                            <span className="font-mono text-xs text-[var(--text-faint)]">
                              {c.hp_current}/{c.hp_max}
                            </span>
                          )}
                        </div>
                        {c ? (
                          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-[var(--surface-2)]">
                            <div
                              className="h-full"
                              style={{
                                width: `${hpPct}%`,
                                background:
                                  hpPct! > 50 ? 'var(--success)' : hpPct! > 20 ? 'var(--accent)' : 'var(--danger)',
                              }}
                            />
                          </div>
                        ) : (
                          <p className="text-xs text-[var(--text-faint)]">
                            {member.sync_error ?? 'No D&D Beyond character linked.'}
                          </p>
                        )}
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </div>
        )}

        {tab === 'sessions' && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="space-y-3 lg:col-span-1">
              <form onSubmit={handleCreateSession} className="space-y-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
                <input
                  value={sessionNumber}
                  onChange={(e) => setSessionNumber(e.target.value.replace(/\D/g, ''))}
                  placeholder="Session #"
                  className="w-full rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)] placeholder-[var(--text-faint)]"
                />
                <button
                  type="submit"
                  disabled={creating || !sessionNumber}
                  className="w-full rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50"
                >
                  New session
                </button>
              </form>

              <ul className="space-y-1">
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
                      <div className="text-xs text-[var(--text-faint)]">
                        {s.date} - {s.processing_status}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            <div className="lg:col-span-2">
              {selected ? (
                <div className="space-y-4 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-[var(--text)]">
                      {selected.campaign_name} - Session {selected.session_number}
                    </h3>
                    <button
                      onClick={() => handleProcess(selected.id)}
                      disabled={selected.processing_status === 'processing'}
                      className="rounded-md border border-[var(--border)] px-3 py-1.5 text-sm hover:bg-[var(--surface-2)] disabled:opacity-50"
                    >
                      {selected.processing_status === 'processing'
                        ? 'Processing...'
                        : selected.processing_status === 'complete'
                          ? 'Re-process'
                          : 'Transcribe + Summarize'}
                    </button>
                  </div>

                  {selected.processing_status === 'error' && (
                    <p className="text-sm text-[var(--danger)]">{selected.processing_error}</p>
                  )}

                  <div>
                    <h4 className="mb-1 text-sm font-semibold uppercase tracking-wide text-[var(--text-faint)]">
                      Master Summary (uncensored)
                    </h4>
                    <p className="whitespace-pre-wrap text-sm text-[var(--text-muted)]">
                      {selected.gm_summary ?? 'Not generated yet.'}
                    </p>
                  </div>

                  <div>
                    <h4 className="mb-1 text-sm font-semibold uppercase tracking-wide text-[var(--text-faint)]">
                      Full Transcript
                    </h4>
                    <pre className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded-md bg-[var(--bg)] p-3 text-xs text-[var(--text-muted)]">
                      {selected.full_transcript ?? 'Not transcribed yet.'}
                    </pre>
                  </div>

                  <NotesPanel token={token} sessionId={selected.id} role="gm" players={players} />
                </div>
              ) : (
                <p className="text-sm text-[var(--text-faint)]">Create or select a session to get started.</p>
              )}
            </div>
          </div>
        )}

        {tab === 'party' && <PartyOverview token={token} />}

        {tab === 'bot' && <BotControlPanel token={token} activeSessionId={selectedId} />}

        {tab === 'soundboard' && <SoundboardPanel token={token} />}

        {tab === 'settings' && <SettingsPanel token={token} focusKey={focusSettingsKey} />}
        </div>
      </div>
    </div>
  )
}
