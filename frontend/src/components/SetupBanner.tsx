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
        <div className="rounded-md border border-red-800 bg-red-950/40 p-3">
          <div className="mb-1 flex items-center justify-between gap-2">
            <h4 className="text-sm font-semibold text-red-300">
              Setup needed ({required.length}) - some features won't work yet
            </h4>
            <button
              type="button"
              onClick={() => onGoToSettings()}
              className="shrink-0 rounded-md bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-500"
            >
              Go to Settings
            </button>
          </div>
          <ul className="space-y-0.5 pl-1 text-xs text-red-200">
            {required.map((item) => (
              <li key={item.key}>
                <button
                  type="button"
                  onClick={() => onGoToSettings(item.key)}
                  className="text-left underline decoration-red-700 hover:text-red-100"
                >
                  {item.message}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {optional.length > 0 && (
        <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
          <div className="mb-1 flex items-center justify-between gap-2">
            <h4 className="text-sm font-semibold text-slate-300">Optional setup ({optional.length})</h4>
            <button
              type="button"
              onClick={() => onGoToSettings()}
              className="shrink-0 rounded-md border border-slate-700 px-2 py-1 text-xs hover:bg-slate-800"
            >
              Go to Settings
            </button>
          </div>
          <ul className="space-y-0.5 pl-1 text-xs text-slate-400">
            {optional.map((item) => (
              <li key={item.key}>
                <button
                  type="button"
                  onClick={() => onGoToSettings(item.key)}
                  className="text-left underline decoration-slate-600 hover:text-slate-200"
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
