import { useState } from 'react'
import { updateMyCharacter } from '../api/resources'
import type { CharacterInput, CharacterPublic, InventoryItemPublic, KnownSpell } from '../types/api'

const ABILITY_NAMES = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
const CURRENCY_NAMES = ['cp', 'sp', 'ep', 'gp', 'pp']
const SPELL_LEVELS = Array.from({ length: 9 }, (_, i) => i + 1) // 1-9, cantrips aren't sloted

function fromExisting(character: CharacterPublic | null): CharacterInput {
  if (!character) {
    return {
      name: '',
      race: '',
      classes: [],
      level: 1,
      proficiency_bonus: 2,
      ability_scores: Object.fromEntries(ABILITY_NAMES.map((n) => [n, 10])),
      hp_current: 10,
      hp_max: 10,
      hp_temp: 0,
      armor_class: 10,
      passive_perception: 10,
      currencies: Object.fromEntries(CURRENCY_NAMES.map((n) => [n, 0])),
      inventory: [],
      spell_slots: {},
      known_spells: [],
    }
  }
  return {
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
    spell_slots: character.spell_slots,
    known_spells: character.known_spells,
  }
}

const inputClass =
  'w-full rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-sm text-[var(--text)]'

export function CharacterEditor({
  token,
  character,
  onSaved,
  onCancel,
}: {
  token: string
  character: CharacterPublic | null
  onSaved: (character: CharacterPublic) => void
  onCancel?: () => void
}) {
  const [form, setForm] = useState<CharacterInput>(() => fromExisting(character))
  const [classesText, setClassesText] = useState(character?.classes.join(', ') ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function update<K extends keyof CharacterInput>(key: K, value: CharacterInput[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  function updateAbility(name: string, value: number) {
    setForm((prev) => ({ ...prev, ability_scores: { ...prev.ability_scores, [name]: value } }))
  }

  function updateCurrency(name: string, value: number) {
    setForm((prev) => ({ ...prev, currencies: { ...prev.currencies, [name]: value } }))
  }

  function updateInventoryItem(index: number, item: InventoryItemPublic) {
    setForm((prev) => ({ ...prev, inventory: prev.inventory.map((it, i) => (i === index ? item : it)) }))
  }

  function addInventoryItem() {
    setForm((prev) => ({ ...prev, inventory: [...prev.inventory, { name: '', quantity: 1, equipped: false }] }))
  }

  function removeInventoryItem(index: number) {
    setForm((prev) => ({ ...prev, inventory: prev.inventory.filter((_, i) => i !== index) }))
  }

  function updateSlotMax(level: number, max: number) {
    setForm((prev) => {
      const key = String(level)
      const existing = prev.spell_slots[key]
      return {
        ...prev,
        spell_slots: { ...prev.spell_slots, [key]: { current: existing ? Math.min(existing.current, max) : max, max } },
      }
    })
  }

  function updateSpell(index: number, spell: KnownSpell) {
    setForm((prev) => ({ ...prev, known_spells: prev.known_spells.map((s, i) => (i === index ? spell : s)) }))
  }

  function addSpell() {
    setForm((prev) => ({ ...prev, known_spells: [...prev.known_spells, { name: '', level: 0, description: '' }] }))
  }

  function removeSpell(index: number) {
    setForm((prev) => ({ ...prev, known_spells: prev.known_spells.filter((_, i) => i !== index) }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload: CharacterInput = {
        ...form,
        classes: classesText
          .split(',')
          .map((c) => c.trim())
          .filter(Boolean),
      }
      const saved = await updateMyCharacter(token, payload)
      onSaved(saved)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save character.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
      <h3 className="text-lg font-semibold text-[var(--text)]">
        {character ? 'Edit your character' : 'Create your character'}
      </h3>
      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <label className="col-span-2 text-xs text-[var(--text-faint)]">
          Name
          <input className={inputClass} value={form.name} onChange={(e) => update('name', e.target.value)} required />
        </label>
        <label className="text-xs text-[var(--text-faint)]">
          Race
          <input className={inputClass} value={form.race} onChange={(e) => update('race', e.target.value)} />
        </label>
        <label className="text-xs text-[var(--text-faint)]">
          Level
          <input
            type="number"
            min={1}
            className={inputClass}
            value={form.level}
            onChange={(e) => update('level', Number(e.target.value))}
          />
        </label>
        <label className="col-span-2 text-xs text-[var(--text-faint)]">
          Classes (comma-separated, e.g. "Fighter 3, Rogue 1")
          <input className={inputClass} value={classesText} onChange={(e) => setClassesText(e.target.value)} />
        </label>
        <label className="text-xs text-[var(--text-faint)]">
          Proficiency bonus
          <input
            type="number"
            className={inputClass}
            value={form.proficiency_bonus}
            onChange={(e) => update('proficiency_bonus', Number(e.target.value))}
          />
        </label>
      </div>

      <div>
        <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--text-faint)]">Ability scores</h4>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
          {ABILITY_NAMES.map((name) => (
            <label key={name} className="text-xs text-[var(--text-faint)]">
              {name}
              <input
                type="number"
                className={inputClass}
                value={form.ability_scores[name] ?? 10}
                onChange={(e) => updateAbility(name, Number(e.target.value))}
              />
            </label>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
        <label className="text-xs text-[var(--text-faint)]">
          HP current
          <input
            type="number"
            className={inputClass}
            value={form.hp_current}
            onChange={(e) => update('hp_current', Number(e.target.value))}
          />
        </label>
        <label className="text-xs text-[var(--text-faint)]">
          HP max
          <input
            type="number"
            className={inputClass}
            value={form.hp_max}
            onChange={(e) => update('hp_max', Number(e.target.value))}
          />
        </label>
        <label className="text-xs text-[var(--text-faint)]">
          HP temp
          <input
            type="number"
            className={inputClass}
            value={form.hp_temp}
            onChange={(e) => update('hp_temp', Number(e.target.value))}
          />
        </label>
        <label className="text-xs text-[var(--text-faint)]">
          Armor Class
          <input
            type="number"
            className={inputClass}
            value={form.armor_class}
            onChange={(e) => update('armor_class', Number(e.target.value))}
          />
        </label>
        <label className="text-xs text-[var(--text-faint)]">
          Passive Perception
          <input
            type="number"
            className={inputClass}
            value={form.passive_perception}
            onChange={(e) => update('passive_perception', Number(e.target.value))}
          />
        </label>
      </div>

      <div>
        <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--text-faint)]">Currency</h4>
        <div className="grid grid-cols-5 gap-2">
          {CURRENCY_NAMES.map((name) => (
            <label key={name} className="text-xs text-[var(--text-faint)]">
              {name}
              <input
                type="number"
                className={inputClass}
                value={form.currencies[name] ?? 0}
                onChange={(e) => updateCurrency(name, Number(e.target.value))}
              />
            </label>
          ))}
        </div>
      </div>

      <div>
        <div className="mb-1 flex items-center justify-between">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-faint)]">Inventory</h4>
          <button type="button" onClick={addInventoryItem} className="text-xs text-[var(--accent)] hover:text-[var(--accent-hover)]">
            + Add item
          </button>
        </div>
        <div className="space-y-1">
          {form.inventory.map((item, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                className={`${inputClass} flex-1`}
                placeholder="Item name"
                value={item.name}
                onChange={(e) => updateInventoryItem(i, { ...item, name: e.target.value })}
              />
              <input
                type="number"
                min={1}
                className={`${inputClass} w-16`}
                value={item.quantity}
                onChange={(e) => updateInventoryItem(i, { ...item, quantity: Number(e.target.value) })}
              />
              <label className="flex items-center gap-1 text-xs text-[var(--text-faint)]">
                <input
                  type="checkbox"
                  checked={item.equipped}
                  onChange={(e) => updateInventoryItem(i, { ...item, equipped: e.target.checked })}
                />
                equipped
              </label>
              <button type="button" onClick={() => removeInventoryItem(i)} className="text-xs text-[var(--danger)]">
                Remove
              </button>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--text-faint)]">Spell slots</h4>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-9">
          {SPELL_LEVELS.map((level) => (
            <label key={level} className="text-xs text-[var(--text-faint)]">
              Lv {level}
              <input
                type="number"
                min={0}
                className={inputClass}
                value={form.spell_slots[String(level)]?.max ?? 0}
                onChange={(e) => updateSlotMax(level, Number(e.target.value))}
              />
            </label>
          ))}
        </div>
      </div>

      <div>
        <div className="mb-1 flex items-center justify-between">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-faint)]">Known spells</h4>
          <button type="button" onClick={addSpell} className="text-xs text-[var(--accent)] hover:text-[var(--accent-hover)]">
            + Add spell
          </button>
        </div>
        <div className="space-y-1">
          {form.known_spells.map((spell, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                className={`${inputClass} flex-1`}
                placeholder="Spell name"
                value={spell.name}
                onChange={(e) => updateSpell(i, { ...spell, name: e.target.value })}
              />
              <select
                className={`${inputClass} w-24`}
                value={spell.level}
                onChange={(e) => updateSpell(i, { ...spell, level: Number(e.target.value) })}
              >
                <option value={0}>Cantrip</option>
                {SPELL_LEVELS.map((level) => (
                  <option key={level} value={level}>
                    Level {level}
                  </option>
                ))}
              </select>
              <input
                className={`${inputClass} flex-1`}
                placeholder="Notes (optional)"
                value={spell.description}
                onChange={(e) => updateSpell(i, { ...spell, description: e.target.value })}
              />
              <button type="button" onClick={() => removeSpell(i)} className="text-xs text-[var(--danger)]">
                Remove
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-[var(--accent)] px-4 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save character'}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-[var(--border)] px-4 py-1.5 text-sm hover:bg-[var(--surface-2)]"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}
