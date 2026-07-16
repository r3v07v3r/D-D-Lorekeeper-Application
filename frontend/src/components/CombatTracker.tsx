import { useEffect, useState } from 'react'
import {
  addCombatant,
  endEncounter,
  getActiveEncounter,
  nextTurn,
  removeCombatant,
  startEncounter,
  updateCombatant,
} from '../api/resources'
import type { CombatantCreate, EncounterPublic, UserPublic } from '../types/api'

// GM-only combat tracker. Damage/healing applied to a player-linked
// combatant here writes through to that player's actual Character.hp_current
// server-side (see backend/app/routers/encounters.py) - there's one HP
// number, not a separate copy that can drift from the character sheet.
export function CombatTracker({ token, players }: { token: string; players: UserPublic[] }) {
  const [encounter, setEncounter] = useState<EncounterPublic | null | undefined>(undefined)
  const [error, setError] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [newUserId, setNewUserId] = useState('')
  const [newInitiative, setNewInitiative] = useState('')

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 5000)
    return () => clearInterval(interval)
  }, [token])

  function refresh() {
    getActiveEncounter(token)
      .then(setEncounter)
      .catch(() => setError('Could not load the combat tracker.'))
  }

  async function handleStart() {
    try {
      setEncounter(await startEncounter(token))
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start an encounter.')
    }
  }

  async function handleAddCombatant(e: React.FormEvent) {
    e.preventDefault()
    if (!encounter) return
    try {
      const payload: CombatantCreate = { initiative: Number(newInitiative) || 0 }
      if (newUserId) payload.user_id = Number(newUserId)
      else payload.name = newName.trim()
      setEncounter(await addCombatant(token, encounter.id, payload))
      setNewName('')
      setNewUserId('')
      setNewInitiative('')
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not add that combatant.')
    }
  }

  async function handleHpDelta(combatantId: number, current: number, max: number, delta: number) {
    if (!encounter) return
    const next = Math.max(0, Math.min(max, current + delta))
    try {
      setEncounter(await updateCombatant(token, encounter.id, combatantId, { hp_current: next }))
    } catch {
      setError('Could not update HP.')
    }
  }

  async function handleRemove(combatantId: number) {
    if (!encounter) return
    try {
      await removeCombatant(token, encounter.id, combatantId)
      refresh()
    } catch {
      setError('Could not remove that combatant.')
    }
  }

  async function handleNextTurn() {
    if (!encounter) return
    try {
      setEncounter(await nextTurn(token, encounter.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not advance the turn.')
    }
  }

  async function handleEnd() {
    if (!encounter) return
    try {
      await endEncounter(token, encounter.id)
      setEncounter(null)
    } catch {
      setError('Could not end the encounter.')
    }
  }

  if (encounter === undefined) {
    return <p className="text-sm text-[var(--text-faint)]">Loading combat tracker...</p>
  }

  if (encounter === null) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
        <h3 className="mb-2 text-lg font-semibold text-[var(--text)]">Combat Tracker</h3>
        {error && <p className="mb-2 text-sm text-[var(--danger)]">{error}</p>}
        <button
          onClick={handleStart}
          className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
        >
          Start Encounter
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-[var(--text)]">
          Combat Tracker <span className="font-normal text-[var(--text-faint)]">- Round {encounter.round}</span>
        </h3>
        <div className="flex gap-2">
          <button
            onClick={handleNextTurn}
            className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
          >
            Next Turn
          </button>
          <button
            onClick={handleEnd}
            className="rounded-md border border-[var(--danger)] px-3 py-1.5 text-sm text-[var(--danger)] hover:bg-[var(--danger-soft)]"
          >
            End Encounter
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

      <form onSubmit={handleAddCombatant} className="flex flex-wrap items-center gap-2 rounded-md border border-[var(--border)] p-2">
        <select
          value={newUserId}
          onChange={(e) => setNewUserId(e.target.value)}
          className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-sm text-[var(--text)]"
        >
          <option value="">Monster / NPC</option>
          {players.map((p) => (
            <option key={p.id} value={p.id}>
              {p.username}
            </option>
          ))}
        </select>
        {!newUserId && (
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Name"
            className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-sm text-[var(--text)]"
          />
        )}
        <input
          type="number"
          value={newInitiative}
          onChange={(e) => setNewInitiative(e.target.value)}
          placeholder="Initiative"
          className="w-24 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-sm text-[var(--text)]"
        />
        <button
          type="submit"
          disabled={!newUserId && !newName.trim()}
          className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50"
        >
          Add
        </button>
      </form>

      {encounter.combatants.length === 0 ? (
        <p className="text-sm text-[var(--text-faint)]">No combatants yet - add one above.</p>
      ) : (
        <ul className="space-y-1">
          {encounter.combatants.map((c, i) => {
            const hpPct = Math.max(0, Math.min(100, (c.hp_current / Math.max(c.hp_max, 1)) * 100))
            const isCurrentTurn = i === encounter.turn_index
            return (
              <li
                key={c.id}
                className={`flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-sm ${
                  isCurrentTurn ? 'border-[var(--accent)] bg-[var(--accent-soft)]/20' : 'border-[var(--border)]'
                }`}
              >
                <span className="w-10 shrink-0 font-mono text-xs text-[var(--text-faint)]">Init {c.initiative}</span>
                <span className="min-w-0 flex-1 truncate font-medium text-[var(--text)]">{c.name}</span>
                <div className="h-1.5 w-24 shrink-0 overflow-hidden rounded-full bg-[var(--surface-2)]">
                  <div
                    className="h-full"
                    style={{
                      width: `${hpPct}%`,
                      background: hpPct > 50 ? 'var(--success)' : hpPct > 20 ? 'var(--accent)' : 'var(--danger)',
                    }}
                  />
                </div>
                <span className="w-16 shrink-0 font-mono text-xs text-[var(--text-faint)]">
                  {c.hp_current}/{c.hp_max}
                </span>
                <span className="w-12 shrink-0 text-xs text-[var(--text-faint)]">AC {c.armor_class}</span>
                <div className="flex shrink-0 gap-1">
                  <button
                    onClick={() => handleHpDelta(c.id, c.hp_current, c.hp_max, -5)}
                    className="rounded border border-[var(--border)] px-1.5 text-xs hover:bg-[var(--surface-2)]"
                  >
                    -5
                  </button>
                  <button
                    onClick={() => handleHpDelta(c.id, c.hp_current, c.hp_max, -1)}
                    className="rounded border border-[var(--border)] px-1.5 text-xs hover:bg-[var(--surface-2)]"
                  >
                    -1
                  </button>
                  <button
                    onClick={() => handleHpDelta(c.id, c.hp_current, c.hp_max, 1)}
                    className="rounded border border-[var(--border)] px-1.5 text-xs hover:bg-[var(--surface-2)]"
                  >
                    +1
                  </button>
                  <button
                    onClick={() => handleHpDelta(c.id, c.hp_current, c.hp_max, 5)}
                    className="rounded border border-[var(--border)] px-1.5 text-xs hover:bg-[var(--surface-2)]"
                  >
                    +5
                  </button>
                  <button
                    onClick={() => handleRemove(c.id)}
                    className="rounded border border-[var(--border)] px-1.5 text-xs text-[var(--danger)] hover:bg-[var(--danger-soft)]"
                  >
                    Remove
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
