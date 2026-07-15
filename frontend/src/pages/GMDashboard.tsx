import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { createSession, listSessions, listUsers, processSession } from '../api/resources'
import { NotesPanel } from '../components/NotesPanel'
import { BotControlPanel } from '../components/BotControlPanel'
import { PartyOverview } from '../components/PartyOverview'
import { SettingsPanel } from '../components/SettingsPanel'
import { SoundboardPanel } from '../components/SoundboardPanel'
import type { SessionLogPublic, UserPublic } from '../types/api'

type Tab = 'sessions' | 'party' | 'bot' | 'soundboard' | 'settings'

export function GMDashboard() {
  const { token } = useAuth()
  const [tab, setTab] = useState<Tab>('sessions')
  const [sessions, setSessions] = useState<SessionLogPublic[]>([])
  const [players, setPlayers] = useState<UserPublic[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [campaignName, setCampaignName] = useState('')
  const [sessionNumber, setSessionNumber] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    if (!token) return
    refreshSessions()
    listUsers()
      .then((all) => setPlayers(all.filter((u) => u.role === 'player')))
      .catch(() => {})
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
    if (!token || !campaignName.trim() || !sessionNumber) return
    setCreating(true)
    try {
      const log = await createSession(token, {
        campaign_name: campaignName.trim(),
        session_number: Number(sessionNumber),
        date: new Date().toISOString().slice(0, 10),
      })
      setCampaignName('')
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

  if (!token) return null

  const selected = sessions.find((s) => s.id === selectedId) ?? null

  return (
    <div className="space-y-4">
      <nav className="flex gap-2 border-b border-slate-800">
        {(['sessions', 'party', 'bot', 'soundboard', 'settings'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm font-medium capitalize ${
              tab === t ? 'border-b-2 border-indigo-500 text-slate-100' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {t === 'bot' ? 'Bot Control' : t}
          </button>
        ))}
      </nav>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {tab === 'sessions' && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="space-y-3 lg:col-span-1">
            <form onSubmit={handleCreateSession} className="space-y-2 rounded-lg border border-slate-800 bg-slate-900 p-3">
              <input
                value={campaignName}
                onChange={(e) => setCampaignName(e.target.value)}
                placeholder="Campaign name"
                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500"
              />
              <input
                value={sessionNumber}
                onChange={(e) => setSessionNumber(e.target.value.replace(/\D/g, ''))}
                placeholder="Session #"
                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500"
              />
              <button
                type="submit"
                disabled={creating || !campaignName.trim() || !sessionNumber}
                className="w-full rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
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
                      selectedId === s.id ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:bg-slate-900'
                    }`}
                  >
                    <div className="font-medium">
                      {s.campaign_name} - Session {s.session_number}
                    </div>
                    <div className="text-xs text-slate-500">
                      {s.date} - {s.processing_status}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <div className="lg:col-span-2">
            {selected ? (
              <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900 p-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-slate-100">
                    {selected.campaign_name} - Session {selected.session_number}
                  </h3>
                  <button
                    onClick={() => handleProcess(selected.id)}
                    disabled={selected.processing_status === 'processing'}
                    className="rounded-md border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-800 disabled:opacity-50"
                  >
                    {selected.processing_status === 'processing'
                      ? 'Processing...'
                      : selected.processing_status === 'complete'
                        ? 'Re-process'
                        : 'Transcribe + Summarize'}
                  </button>
                </div>

                {selected.processing_status === 'error' && (
                  <p className="text-sm text-red-400">{selected.processing_error}</p>
                )}

                <div>
                  <h4 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500">
                    Master Summary (uncensored)
                  </h4>
                  <p className="whitespace-pre-wrap text-sm text-slate-300">
                    {selected.gm_summary ?? 'Not generated yet.'}
                  </p>
                </div>

                <div>
                  <h4 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500">
                    Full Transcript
                  </h4>
                  <pre className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded-md bg-slate-950 p-3 text-xs text-slate-400">
                    {selected.full_transcript ?? 'Not transcribed yet.'}
                  </pre>
                </div>

                <NotesPanel token={token} sessionId={selected.id} role="gm" players={players} />
              </div>
            ) : (
              <p className="text-sm text-slate-500">Create or select a session to get started.</p>
            )}
          </div>
        </div>
      )}

      {tab === 'party' && <PartyOverview token={token} />}

      {tab === 'bot' && <BotControlPanel token={token} activeSessionId={selectedId} />}

      {tab === 'soundboard' && <SoundboardPanel token={token} />}

      {tab === 'settings' && <SettingsPanel token={token} />}
    </div>
  )
}
