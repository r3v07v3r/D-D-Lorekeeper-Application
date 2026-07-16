import type { HighlightPublic } from '../types/api'

// Colors are semantic (category), separate from the theme accent - a
// warning/critical stripe means the same thing regardless of which theme
// preset is active (see theme/ThemeContext.tsx).
const CATEGORY_STYLE: Record<HighlightPublic['category'], string> = {
  damage: 'bg-[var(--danger-soft)] text-[var(--danger)]',
  kill: 'bg-[var(--danger-soft)] text-[var(--danger)]',
  death: 'bg-[var(--danger-soft)] text-[var(--danger)]',
  critical: 'bg-[var(--success)]/20 text-[var(--success)]',
  strange: 'bg-[var(--accent-soft)] text-[var(--accent)]',
  other: 'bg-[var(--surface-2)] text-[var(--text-muted)]',
}

const CATEGORY_LABEL: Record<HighlightPublic['category'], string> = {
  damage: 'Damage',
  kill: 'Kill',
  death: 'Down',
  critical: 'Critical',
  strange: 'Strange',
  other: 'Moment',
}

// LLM-extracted from the session's real transcript (grounded against
// actually-logged dice rolls where available - see
// backend/app/ai/summarization.py:generate_highlights). Never fabricated
// placeholder content: an empty list just isn't rendered.
export function SessionHighlights({ highlights }: { highlights: HighlightPublic[] }) {
  if (highlights.length === 0) return null

  return (
    <div>
      <h4 className="mb-1 text-sm font-semibold uppercase tracking-wide text-[var(--text-faint)]">Highlights</h4>
      <ul className="space-y-1.5">
        {highlights.map((h, i) => (
          <li key={i} className="flex items-start gap-2 text-sm">
            <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${CATEGORY_STYLE[h.category]}`}>
              {CATEGORY_LABEL[h.category]}
            </span>
            <span className="text-[var(--text-muted)]">{h.description}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
