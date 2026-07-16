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
    <div className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
      <h4 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-faint)]">Bot Control</h4>
      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
      {status ? (
        <div className="flex flex-wrap items-center gap-2 text-sm text-[var(--text-muted)]">
          <span>
            Voice: <span className={status.connected ? 'text-[var(--success)]' : 'text-[var(--text-faint)]'}>{status.connected ? 'connected' : 'not connected'}</span>
          </span>
          <span>
            Recording: <span className={status.is_recording ? 'text-[var(--danger)]' : 'text-[var(--text-faint)]'}>{status.is_recording ? 'yes' : 'no'}</span>
          </span>
        </div>
      ) : (
        <p className="text-sm text-[var(--text-faint)]">Loading status...</p>
      )}

      {!status?.connected ? (
        <div>
          <div className="flex gap-2">
            <input
              value={channelId}
              onChange={(e) => setChannelId(e.target.value)}
              placeholder="Discord voice channel ID"
              className="flex-1 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)] placeholder-[var(--text-faint)]"
            />
            <button
              disabled={busy || !channelId.trim()}
              onClick={() => withBusy(() => joinVoiceChannel(token, Number(channelId.trim())))}
              className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50"
            >
              Join
            </button>
          </div>
          <p className="mt-1 text-xs text-[var(--text-faint)]">
            Don't know the ID? In Discord, enable <strong>Settings → Advanced → Developer Mode</strong>,
            then right-click the voice channel and choose <strong>Copy Channel ID</strong>.
          </p>
        </div>
      ) : (
        <button
          disabled={busy || status.is_recording}
          onClick={() => withBusy(() => leaveVoiceChannel(token))}
          className="rounded-md border border-[var(--border)] px-3 py-1.5 text-sm hover:bg-[var(--surface-2)] disabled:opacity-50"
        >
          Leave voice channel
        </button>
      )}

      {status?.connected && !status.is_recording && (
        <button
          disabled={busy || !activeSessionId}
          onClick={() => activeSessionId && withBusy(() => startRecording(token, activeSessionId))}
          className="rounded-md bg-[var(--danger)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--danger-hover)] disabled:opacity-50"
          title={activeSessionId ? undefined : 'Select or create a session first'}
        >
          Start recording
        </button>
      )}
      {status?.is_recording && (
        <button
          disabled={busy}
          onClick={() => withBusy(() => stopRecording(token))}
          className="rounded-md border border-[var(--danger)] px-3 py-1.5 text-sm text-[var(--danger)] hover:bg-[var(--danger-soft)] disabled:opacity-50"
        >
          Stop recording
        </button>
      )}
    </div>
  )
}
