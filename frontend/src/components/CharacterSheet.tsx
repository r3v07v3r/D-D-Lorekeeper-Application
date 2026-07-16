import { restCharacter, updateMyCharacter } from '../api/resources'
import type { CharacterPublic } from '../types/api'

function StatBlock({ label, value, estimate }: { label: string; value: number; estimate?: boolean }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-center">
      <div className="text-2xl font-semibold text-[var(--text)]">
        {value}
        {estimate && <span title="Estimated - may not exactly match D&D Beyond for unusual features">*</span>}
      </div>
      <div className="text-xs uppercase tracking-wide text-[var(--text-faint)]">{label}</div>
    </div>
  )
}

// `editable`+`token` are only passed by the character's own owner (see
// PlayerDashboard.tsx) - the GM's read-only Party Overview (PartyOverview.tsx)
// renders this same component with neither, so spell-slot consumption and
// the rest button never show up there.
export function CharacterSheet({
  character,
  editable,
  token,
  onUpdated,
}: {
  character: CharacterPublic
  editable?: boolean
  token?: string
  onUpdated?: (character: CharacterPublic) => void
}) {
  const hpPct = Math.max(0, Math.min(100, (character.hp_current / Math.max(character.hp_max, 1)) * 100))
  const spellLevels = Object.keys(character.spell_slots)
    .map(Number)
    .sort((a, b) => a - b)

  async function adjustSlot(level: number, delta: number) {
    if (!token) return
    const key = String(level)
    const slot = character.spell_slots[key]
    if (!slot) return
    const nextCurrent = Math.max(0, Math.min(slot.max, slot.current + delta))
    const updated = await updateMyCharacter(token, {
      name: character.name,
      race: character.race,
      classes: character.classes,
      level: character.level,
      proficiency_bonus: character.proficiency_bonus,
      ability_scores: character.ability_scores,
      hp_current: character.hp_current,
      hp_max: character.hp_max,
      hp_temp: character.hp_temp,
      armor_class: character.armor_class,
      passive_perception: character.passive_perception,
      currencies: character.currencies,
      inventory: character.inventory,
      spell_slots: { ...character.spell_slots, [key]: { current: nextCurrent, max: slot.max } },
      known_spells: character.known_spells,
    })
    onUpdated?.(updated)
  }

  async function handleLongRest() {
    if (!token) return
    const updated = await restCharacter(token)
    onUpdated?.(updated)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-[var(--text)]">{character.name}</h3>
          <p className="text-sm text-[var(--text-muted)]">
            {character.race} - {character.classes.join(' / ')} (Level {character.level})
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-[var(--surface-2)] px-2 py-0.5 text-[10px] uppercase tracking-wide text-[var(--text-faint)]">
            {character.source === 'dndbeyond' ? 'Synced from D&D Beyond' : 'Manual'}
          </span>
          {editable && (
            <button
              onClick={handleLongRest}
              className="rounded-md border border-[var(--border)] px-2 py-1 text-xs hover:bg-[var(--surface-2)]"
              title="Restores HP to max, clears temp HP, and restores all spell slots"
            >
              Long Rest
            </button>
          )}
        </div>
      </div>

      <div>
        <div className="mb-1 flex justify-between text-sm text-[var(--text-muted)]">
          <span>
            HP {character.hp_current} / {character.hp_max}
            {character.hp_temp > 0 && ` (+${character.hp_temp} temp)`}
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--surface-2)]">
          <div
            className={`h-full ${hpPct > 50 ? 'bg-[var(--success)]' : hpPct > 20 ? 'bg-[var(--accent)]' : 'bg-[var(--danger)]'}`}
            style={{ width: `${hpPct}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        <StatBlock label="AC" value={character.armor_class} estimate={character.armor_class_is_estimate} />
        <StatBlock
          label="Passive Perception"
          value={character.passive_perception}
          estimate={character.passive_perception_is_estimate}
        />
        <StatBlock label="Proficiency" value={character.proficiency_bonus} />
        <StatBlock label="Gold" value={character.currencies.gp ?? 0} />
      </div>

      <div className="grid grid-cols-6 gap-2 text-center">
        {Object.entries(character.ability_scores).map(([name, score]) => (
          <div key={name} className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2 py-2">
            <div className="text-xs uppercase text-[var(--text-faint)]">{name}</div>
            <div className="text-lg font-semibold text-[var(--text)]">{score}</div>
            <div className="text-xs text-[var(--text-faint)]">
              {character.ability_modifiers[name] >= 0 ? '+' : ''}
              {character.ability_modifiers[name]}
            </div>
          </div>
        ))}
      </div>

      {(character.armor_class_is_estimate || character.passive_perception_is_estimate) && (
        <p className="text-xs text-[var(--text-faint)]">* Estimated from synced data - may not match D&D Beyond exactly for unusual class features or feats.</p>
      )}

      {spellLevels.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide text-[var(--text-faint)]">Spell Slots</h4>
          <div className="flex flex-wrap gap-2">
            {spellLevels.map((level) => {
              const slot = character.spell_slots[String(level)]
              return (
                <div
                  key={level}
                  className="flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-sm"
                >
                  <span className="text-xs text-[var(--text-faint)]">Lv {level}</span>
                  {editable && (
                    <button
                      onClick={() => adjustSlot(level, -1)}
                      disabled={slot.current <= 0}
                      className="text-[var(--text-faint)] hover:text-[var(--text)] disabled:opacity-30"
                    >
                      -
                    </button>
                  )}
                  <span className="font-mono text-[var(--text)]">
                    {slot.current}/{slot.max}
                  </span>
                  {editable && (
                    <button
                      onClick={() => adjustSlot(level, 1)}
                      disabled={slot.current >= slot.max}
                      className="text-[var(--text-faint)] hover:text-[var(--text)] disabled:opacity-30"
                    >
                      +
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {character.known_spells.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide text-[var(--text-faint)]">Known Spells</h4>
          <ul className="space-y-1 text-sm">
            {character.known_spells.map((spell, i) => (
              <li key={i} className="rounded border border-[var(--border)]/60 px-2 py-1">
                <span className="font-medium text-[var(--text)]">{spell.name}</span>{' '}
                <span className="text-xs text-[var(--text-faint)]">
                  ({spell.level === 0 ? 'Cantrip' : `Level ${spell.level}`})
                </span>
                {spell.description && <p className="text-xs text-[var(--text-muted)]">{spell.description}</p>}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide text-[var(--text-faint)]">Inventory</h4>
        <ul className="max-h-64 space-y-1 overflow-y-auto text-sm">
          {character.inventory.map((item, i) => (
            <li key={i} className="flex justify-between rounded border border-[var(--border)]/60 px-2 py-1">
              <span className={item.equipped ? 'text-[var(--text)]' : 'text-[var(--text-muted)]'}>
                {item.name}
                {item.equipped && <span className="ml-2 text-xs text-[var(--success)]">equipped</span>}
              </span>
              <span className="text-[var(--text-faint)]">x{item.quantity}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
