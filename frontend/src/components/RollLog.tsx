import { useEffect, useRef, useState } from 'react'
import { listRolls } from '../api/resources'
import type { RollPublic } from '../types/api'

// Shared, campaign-wide dice-roll feed - polled (same pattern as presence,
// see GMDashboard.tsx), not a websocket, consistent with the rest of this
// app's architecture. Rolls are posted by components/DiceRoller.tsx.
export function RollLog({ token }: { token: string }) {
  const [rolls, setRolls] = useState<RollPublic[]>([])
  const lastIdRef = useRef(0)

  useEffect(() => {
    let cancelled = false
    function refresh() {
      listRolls(token, lastIdRef.current)
        .then((newRolls) => {
          if (cancelled || newRolls.length === 0) return
          lastIdRef.current = newRolls[newRolls.length - 1].id
          setRolls((prev) => [...newRolls, ...prev].slice(0, 50))
        })
        .catch(() => {})
    }
    refresh()
    const interval = setInterval(refresh, 3000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [token])

  return (
    <div className="space-y-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
      <h4 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-faint)]">Roll Log</h4>
      {rolls.length === 0 ? (
        <p className="text-sm text-[var(--text-faint)]">No rolls yet this campaign.</p>
      ) : (
        <ul className="max-h-72 space-y-1 overflow-y-auto text-sm">
          {rolls.map((roll) => (
            <li key={roll.id} className="flex items-center justify-between rounded border border-[var(--border)]/60 px-2 py-1">
              <span className="text-[var(--text-muted)]">
                <span className="font-medium text-[var(--text)]">{roll.username}</span>: {roll.summary}
              </span>
              <span className="font-mono font-semibold text-[var(--text)]">{roll.total}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
