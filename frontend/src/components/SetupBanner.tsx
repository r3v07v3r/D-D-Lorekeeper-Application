import type { SetupItem } from '../types/api'

// Renders whatever app/routers/settings.py:_compute_setup_items() reports as
// unfinished - one source of truth for what "configured" means per field
// lives there, this just displays it. "required" items mean a core feature
// won't work at all yet; "optional" ones are fine to leave for solo play.
export function SetupBanner({
  items,
  onGoToSettings,
}: {
  items: SetupItem[]
  // Called with the specific item's key to jump straight to that field in
  // Settings, or with no argument for the header button's general "just
  // switch to the tab" behavior.
  onGoToSettings: (key?: string) => void
}) {
  if (items.length === 0) return null

  const required = items.filter((i) => i.severity === 'required')
  const optional = items.filter((i) => i.severity === 'optional')

  return (
    <div className="space-y-2">
      {required.length > 0 && (
        <div className="rounded-md border border-[var(--danger)] bg-[var(--danger-soft)]/40 p-3">
          <div className="mb-1 flex items-center justify-between gap-2">
            <h4 className="text-sm font-semibold text-[var(--danger)]">
              Setup needed ({required.length}) - some features won't work yet
            </h4>
            <button
              type="button"
              onClick={() => onGoToSettings()}
              className="shrink-0 rounded-md bg-[var(--danger)] px-2 py-1 text-xs font-medium text-white hover:bg-[var(--danger-hover)]"
            >
              Go to Settings
            </button>
          </div>
          <ul className="space-y-0.5 pl-1 text-xs text-[var(--danger)]">
            {required.map((item) => (
              <li key={item.key}>
                <button
                  type="button"
                  onClick={() => onGoToSettings(item.key)}
                  className="text-left underline decoration-[var(--danger)] hover:text-[var(--danger-hover)]"
                >
                  {item.message}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {optional.length > 0 && (
        <div className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-3">
          <div className="mb-1 flex items-center justify-between gap-2">
            <h4 className="text-sm font-semibold text-[var(--text-muted)]">Optional setup ({optional.length})</h4>
            <button
              type="button"
              onClick={() => onGoToSettings()}
              className="shrink-0 rounded-md border border-[var(--border)] px-2 py-1 text-xs hover:bg-[var(--surface-2)]"
            >
              Go to Settings
            </button>
          </div>
          <ul className="space-y-0.5 pl-1 text-xs text-[var(--text-muted)]">
            {optional.map((item) => (
              <li key={item.key}>
                <button
                  type="button"
                  onClick={() => onGoToSettings(item.key)}
                  className="text-left underline decoration-[var(--text-faint)] hover:text-[var(--text)]"
                >
                  {item.message}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
