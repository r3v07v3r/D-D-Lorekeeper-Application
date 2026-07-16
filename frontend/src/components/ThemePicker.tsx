import { THEME_PRESETS, useTheme } from '../theme/ThemeContext'

export function ThemePicker() {
  const { theme, customAccent, setTheme, setCustomAccent } = useTheme()

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {THEME_PRESETS.map((preset) => (
          <button
            key={preset.value}
            type="button"
            onClick={() => setTheme(preset.value)}
            className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs font-medium ${
              theme === preset.value
                ? 'border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--text)]'
                : 'border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text)]'
            }`}
          >
            <span
              className="h-3 w-3 rounded-full border border-[var(--border)]"
              style={{ background: preset.value === 'custom' ? customAccent : preset.swatch }}
            />
            {preset.label}
          </button>
        ))}
      </div>
      {theme === 'custom' && (
        <div className="mt-2 flex items-center gap-2">
          <input
            type="color"
            value={customAccent}
            onChange={(e) => setCustomAccent(e.target.value)}
            className="h-8 w-12 cursor-pointer rounded border border-[var(--border)] bg-transparent"
          />
          <span className="text-xs text-[var(--text-faint)]">Pick your own accent color</span>
        </div>
      )}
    </div>
  )
}
