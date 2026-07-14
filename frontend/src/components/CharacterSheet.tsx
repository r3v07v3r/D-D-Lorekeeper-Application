import type { CharacterPublic } from '../types/api'

function StatBlock({ label, value, estimate }: { label: string; value: number; estimate?: boolean }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-center">
      <div className="text-2xl font-semibold text-slate-100">
        {value}
        {estimate && <span title="Estimated - may not exactly match D&D Beyond for unusual features">*</span>}
      </div>
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
    </div>
  )
}

export function CharacterSheet({ character }: { character: CharacterPublic }) {
  const hpPct = Math.max(0, Math.min(100, (character.hp_current / Math.max(character.hp_max, 1)) * 100))

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-slate-100">{character.name}</h3>
        <p className="text-sm text-slate-400">
          {character.race} - {character.classes.join(' / ')} (Level {character.level})
        </p>
      </div>

      <div>
        <div className="mb-1 flex justify-between text-sm text-slate-400">
          <span>
            HP {character.hp_current} / {character.hp_max}
            {character.hp_temp > 0 && ` (+${character.hp_temp} temp)`}
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className={`h-full ${hpPct > 50 ? 'bg-emerald-500' : hpPct > 20 ? 'bg-amber-500' : 'bg-red-500'}`}
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
          <div key={name} className="rounded-lg border border-slate-800 bg-slate-900 px-2 py-2">
            <div className="text-xs uppercase text-slate-500">{name}</div>
            <div className="text-lg font-semibold text-slate-100">{score}</div>
            <div className="text-xs text-slate-500">
              {character.ability_modifiers[name] >= 0 ? '+' : ''}
              {character.ability_modifiers[name]}
            </div>
          </div>
        ))}
      </div>

      {(character.armor_class_is_estimate || character.passive_perception_is_estimate) && (
        <p className="text-xs text-slate-600">* Estimated from synced data - may not match D&D Beyond exactly for unusual class features or feats.</p>
      )}

      <div>
        <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Inventory</h4>
        <ul className="max-h-64 space-y-1 overflow-y-auto text-sm">
          {character.inventory.map((item, i) => (
            <li key={i} className="flex justify-between rounded border border-slate-800/60 px-2 py-1">
              <span className={item.equipped ? 'text-slate-100' : 'text-slate-400'}>
                {item.name}
                {item.equipped && <span className="ml-2 text-xs text-emerald-400">equipped</span>}
              </span>
              <span className="text-slate-500">x{item.quantity}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
