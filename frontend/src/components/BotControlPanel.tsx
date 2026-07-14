import { useEffect, useState } from 'react'
import { getBotStatus, joinVoiceChannel, leaveVoiceChannel, startRecording, stopRecording } from '../api/resources'
import type { BotStatusResponse } from '../types/api'

export function BotControlPanel({ token, activeSessionId }: { token: string; activeSessionId: number | null }) {
  const [status, setStatus] = useState<BotStatusResponse | null>(null)
  const [channelId, setChannelId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 5000)
    return () => clearInterval(interval)
  }, [])

  async function refresh() {
    try {
      setStatus(await getBotStatus(token))
      setError(null)
    } catch {
      setError('Could not reach the bot-control API.')
    }
  }

  async function withBusy(fn: () => Promise<void>) {
    setBusy(true)
    try {
      await fn()
      await refresh()
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3 rounded-lg border border-slate-800 bg-slate-900 p-4">
      <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Bot Control</h4>
      {error && <p className="text-sm text-red-400">{error}</p>}
      {status ? (
        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-400">
          <span>
            Voice: <span className={status.connected ? 'text-emerald-400' : 'text-slate-500'}>{status.connected ? 'connected' : 'not connected'}</span>
          </span>
          <span>
            Recording: <span className={status.is_recording ? 'text-red-400' : 'text-slate-500'}>{status.is_recording ? 'yes' : 'no'}</span>
          </span>
        </div>
      ) : (
        <p className="text-sm text-slate-500">Loading status...</p>
      )}

      {!status?.connected ? (
        <div className="flex gap-2">
          <input
            value={channelId}
            onChange={(e) => setChannelId(e.target.value)}
            placeholder="Discord voice channel ID"
            className="flex-1 rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500"
          />
          <button
            disabled={busy || !channelId.trim()}
            onClick={() => withBusy(() => joinVoiceChannel(token, Number(channelId.trim())))}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            Join
          </button>
        </div>
      ) : (
        <button
          disabled={busy || status.is_recording}
          onClick={() => withBusy(() => leaveVoiceChannel(token))}
          className="rounded-md border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-800 disabled:opacity-50"
        >
          Leave voice channel
        </button>
      )}

      {status?.connected && !status.is_recording && (
        <button
          disabled={busy || !activeSessionId}
          onClick={() => activeSessionId && withBusy(() => startRecording(token, activeSessionId))}
          className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-500 disabled:opacity-50"
          title={activeSessionId ? undefined : 'Select or create a session first'}
        >
          Start recording
        </button>
      )}
      {status?.is_recording && (
        <button
          disabled={busy}
          onClick={() => withBusy(() => stopRecording(token))}
          className="rounded-md border border-red-700 px-3 py-1.5 text-sm text-red-300 hover:bg-red-950 disabled:opacity-50"
        >
          Stop recording
        </button>
      )}
    </div>
  )
}
