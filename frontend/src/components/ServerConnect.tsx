import { useState } from 'react'
import { api } from '../api/client'
import { getServerConfig, setServerConfig } from '../api/serverConfig'
import { decodeShareCode } from '../api/shareCode'

// Lets a player point this copy of the app at the GM's machine instead of
// its own local backend (which keeps running regardless - see
// electron/main.js - it's just unused in that case). The GM leaves this on
// its default ("This computer") and generates a share code in their
// Settings tab for players to paste here.
export function ServerConnect({ onChanged }: { onChanged: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const config = getServerConfig()
  const isLocal = config.baseUrl.includes('127.0.0.1') || config.baseUrl.includes('localhost')

  const [code, setCode] = useState('')
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function handleUseThisComputer() {
    setServerConfig({ baseUrl: 'https://127.0.0.1:8000', passphrase: '', fingerprint: null })
    setExpanded(false)
    setError(null)
    onChanged()
  }

  async function handleConnect(e: React.FormEvent) {
    e.preventDefault()
    if (!code.trim()) return
    setConnecting(true)
    setError(null)

    let payload
    try {
      payload = decodeShareCode(code)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not read that share code.')
      setConnecting(false)
      return
    }

    // A GM's LAN and public addresses share the exact same certificate (one
    // server, one cert), so trusting the fingerprint once covers whichever
    // address actually ends up working below.
    const candidates = [payload.lanIp, payload.publicIp].filter((ip): ip is string => Boolean(ip))
    if (candidates.length === 0) {
      setError('That share code has no address in it - ask your GM to generate a new one.')
      setConnecting(false)
      return
    }

    let connected = false
    for (const ip of candidates) {
      setServerConfig({
        baseUrl: `https://${ip}:${payload.port}`,
        passphrase: payload.passphrase,
        fingerprint: payload.fingerprint,
      })
      try {
        await api.get('/users')
        connected = true
        break
      } catch {
        continue // try the next candidate address, if any
      }
    }

    setConnecting(false)
    if (!connected) {
      setError("Couldn't reach your GM at either address in that code. Ask them to check port forwarding, or that they're online.")
    }
    setExpanded(false)
    onChanged()
  }

  return (
    <div className="mb-4 rounded-lg border border-[var(--border)] bg-[var(--bg)]/50 p-3 text-sm">
      <div className="flex items-center justify-between">
        <span className="text-[var(--text-muted)]">
          Server: <span className="text-[var(--text)]">{isLocal ? 'This computer' : config.baseUrl}</span>
        </span>
        <button onClick={() => setExpanded((v) => !v)} className="text-[var(--accent)] hover:text-[var(--accent-hover)]">
          {expanded ? 'Cancel' : "Joining someone else's game?"}
        </button>
      </div>

      {expanded && (
        <form onSubmit={handleConnect} className="mt-3 space-y-2">
          <p className="text-xs text-[var(--text-faint)]">Paste the share code your GM sent you (from their Settings tab).</p>
          {error && <p className="text-xs text-[var(--danger)]">{error}</p>}
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Paste share code here"
            rows={3}
            className="w-full rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 font-mono text-xs text-[var(--text)] placeholder-[var(--text-faint)]"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={connecting || !code.trim()}
              className="rounded-md bg-[var(--accent)] px-3 py-1.5 font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50"
            >
              {connecting ? 'Connecting...' : 'Connect'}
            </button>
            {!isLocal && (
              <button
                type="button"
                onClick={handleUseThisComputer}
                className="rounded-md border border-[var(--border)] px-3 py-1.5 text-[var(--text-muted)] hover:bg-[var(--surface-2)]"
              >
                Use this computer instead
              </button>
            )}
          </div>
        </form>
      )}
    </div>
  )
}
