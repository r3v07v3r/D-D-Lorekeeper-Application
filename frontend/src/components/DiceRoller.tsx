import { useState } from 'react'
import { createRoll } from '../api/resources'
import { rollD20, rollDamage, type D20RollResult, type DamageRollResult } from '../utils/diceEngine'

type Roll = (D20RollResult & { kind: 'd20' }) | (DamageRollResult & { kind: 'damage' })

function d20Summary(roll: D20RollResult): string {
  const advantageNote = roll.advantage !== 'normal' ? ` (${roll.advantage})` : ''
  const modifierNote = roll.modifier !== 0 ? ` ${roll.modifier >= 0 ? '+' : ''}${roll.modifier}` : ''
  return `d20${advantageNote} [${roll.rolls.join(', ')}]${modifierNote} = ${roll.total}`
}

function damageSummary(roll: DamageRollResult): string {
  const critNote = roll.crit ? ' (x2 crit)' : ''
  const modifierNote = roll.modifier !== 0 ? ` ${roll.modifier >= 0 ? '+' : ''}${roll.modifier}` : ''
  return `${roll.diceCount}${critNote}d${roll.diceSides}${modifierNote} [${roll.dice.join(', ')}] = ${roll.total}`
}

// Rolls are broadcast to the shared, campaign-wide roll log (see
// components/RollLog.tsx and backend/app/routers/rolls.py) in addition to
// this component's own instant local history - broadcasting is
// best-effort (fire-and-forget) so a slow/offline connection never blocks
// seeing your own roll immediately. 5e RAW: a critical hit doubles the
// number of damage dice, never the flat modifier - see diceEngine.ts.
export function DiceRoller({ token }: { token: string }) {
  const [modifier, setModifier] = useState(0)
  const [advantage, setAdvantage] = useState<D20RollResult['advantage']>('normal')
  const [diceCount, setDiceCount] = useState(1)
  const [diceSides, setDiceSides] = useState(6)
  const [crit, setCrit] = useState(false)
  const [history, setHistory] = useState<Roll[]>([])

  function handleRollD20() {
    const roll = rollD20(modifier, advantage)
    setHistory((prev) => [{ ...roll, kind: 'd20' as const }, ...prev].slice(0, 20))
    createRoll(token, { summary: d20Summary(roll), total: roll.total }).catch(() => {})
  }

  function handleRollDamage() {
    const roll = rollDamage(diceCount, diceSides, modifier, crit)
    setHistory((prev) => [{ ...roll, kind: 'damage' as const }, ...prev].slice(0, 20))
    createRoll(token, { summary: damageSummary(roll), total: roll.total }).catch(() => {})
  }

  return (
    <div className="space-y-4 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
      <h3 className="text-lg font-semibold text-[var(--text)]">Dice Roller</h3>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-2 rounded-md border border-[var(--border)] p-3">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-faint)]">
            Ability check / attack roll (d20)
          </h4>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <label className="flex items-center gap-1 text-[var(--text-faint)]">
              Modifier
              <input
                type="number"
                value={modifier}
                onChange={(e) => setModifier(Number(e.target.value))}
                className="w-16 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-[var(--text)]"
              />
            </label>
            <select
              value={advantage}
              onChange={(e) => setAdvantage(e.target.value as D20RollResult['advantage'])}
              className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-sm text-[var(--text)]"
            >
              <option value="normal">Normal</option>
              <option value="advantage">Advantage</option>
              <option value="disadvantage">Disadvantage</option>
            </select>
            <button
              onClick={handleRollD20}
              className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
            >
              Roll d20
            </button>
          </div>
        </div>

        <div className="space-y-2 rounded-md border border-[var(--border)] p-3">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-faint)]">Damage roll</h4>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <input
              type="number"
              min={1}
              value={diceCount}
              onChange={(e) => setDiceCount(Number(e.target.value))}
              className="w-14 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-[var(--text)]"
            />
            <span className="text-[var(--text-faint)]">d</span>
            <select
              value={diceSides}
              onChange={(e) => setDiceSides(Number(e.target.value))}
              className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-[var(--text)]"
            >
              {[4, 6, 8, 10, 12, 20].map((sides) => (
                <option key={sides} value={sides}>
                  d{sides}
                </option>
              ))}
            </select>
            <span className="text-[var(--text-faint)]">+</span>
            <input
              type="number"
              value={modifier}
              onChange={(e) => setModifier(Number(e.target.value))}
              className="w-16 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-[var(--text)]"
            />
            <label className="flex items-center gap-1 text-xs text-[var(--text-faint)]" title="Doubles the dice, not the modifier - 5e RAW">
              <input type="checkbox" checked={crit} onChange={(e) => setCrit(e.target.checked)} />
              Critical hit
            </label>
            <button
              onClick={handleRollDamage}
              className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
            >
              Roll damage
            </button>
          </div>
        </div>
      </div>

      {history.length > 0 && (
        <div>
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--text-faint)]">Recent rolls</h4>
          <ul className="max-h-56 space-y-1 overflow-y-auto text-sm">
            {history.map((roll, i) => (
              <li key={i} className="flex items-center justify-between rounded border border-[var(--border)]/60 px-2 py-1">
                {roll.kind === 'd20' ? (
                  <>
                    <span className="text-[var(--text-muted)]">
                      d20{roll.advantage !== 'normal' ? ` (${roll.advantage})` : ''} [{roll.rolls.join(', ')}]
                      {roll.modifier !== 0 && ` ${roll.modifier >= 0 ? '+' : ''}${roll.modifier}`}
                      {roll.isCrit && <span className="ml-1 text-[var(--success)]">crit!</span>}
                      {roll.isFumble && <span className="ml-1 text-[var(--danger)]">fumble</span>}
                    </span>
                    <span className="font-mono font-semibold text-[var(--text)]">{roll.total}</span>
                  </>
                ) : (
                  <>
                    <span className="text-[var(--text-muted)]">
                      {roll.diceCount}
                      {roll.crit ? ` (x2 crit)` : ''}d{roll.diceSides}
                      {roll.modifier !== 0 && ` ${roll.modifier >= 0 ? '+' : ''}${roll.modifier}`} [{roll.dice.join(', ')}]
                    </span>
                    <span className="font-mono font-semibold text-[var(--text)]">{roll.total}</span>
                  </>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
