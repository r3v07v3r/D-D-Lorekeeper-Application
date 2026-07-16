import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export type ThemeName = 'ink-brass' | 'moonlit-slate' | 'verdant-grove' | 'custom'

export const THEME_PRESETS: { value: ThemeName; label: string; swatch: string }[] = [
  { value: 'ink-brass', label: 'Ink & Brass', swatch: '#d89b3c' },
  { value: 'moonlit-slate', label: 'Moonlit Slate', swatch: '#5fb8c9' },
  { value: 'verdant-grove', label: 'Verdant Grove', swatch: '#d8b23c' },
  { value: 'custom', label: 'Custom', swatch: '' },
]

const STORAGE_KEY = 'lorekeeper_theme'
const DEFAULT_CUSTOM_ACCENT = '#d89b3c'

interface ThemeState {
  theme: ThemeName
  customAccent: string
}

interface ThemeContextValue extends ThemeState {
  setTheme: (theme: ThemeName) => void
  setCustomAccent: (hex: string) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

function loadStored(): ThemeState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { theme: 'ink-brass', customAccent: DEFAULT_CUSTOM_ACCENT }
    const parsed = JSON.parse(raw) as Partial<ThemeState>
    return {
      theme: parsed.theme ?? 'ink-brass',
      customAccent: parsed.customAccent ?? DEFAULT_CUSTOM_ACCENT,
    }
  } catch {
    return { theme: 'ink-brass', customAccent: DEFAULT_CUSTOM_ACCENT }
  }
}

// Relative-luminance threshold, not a fixed light/dark accent list - so any
// custom hue (including mid-tone ones we can't anticipate) still gets
// legible text on top of it.
function contrastColorFor(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255
  const luminance = 0.299 * r + 0.587 * g + 0.114 * b
  return luminance > 0.6 ? '#1c1408' : '#ffffff'
}

function softColorFor(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, 0.16)`
}

// Lightens toward white by ~22% for a hover state, rather than requiring the
// user to pick two colors for one "accent" choice.
function hoverColorFor(hex: string): string {
  const mix = (channel: number) => Math.round(channel + (255 - channel) * 0.22)
  const r = mix(parseInt(hex.slice(1, 3), 16))
  const g = mix(parseInt(hex.slice(3, 5), 16))
  const b = mix(parseInt(hex.slice(5, 7), 16))
  return `#${[r, g, b].map((c) => c.toString(16).padStart(2, '0')).join('')}`
}

function applyToDocument(state: ThemeState) {
  const root = document.documentElement
  root.setAttribute('data-theme', state.theme)
  if (state.theme === 'custom') {
    root.style.setProperty('--accent', state.customAccent)
    root.style.setProperty('--accent-hover', hoverColorFor(state.customAccent))
    root.style.setProperty('--accent-contrast', contrastColorFor(state.customAccent))
    root.style.setProperty('--accent-soft', softColorFor(state.customAccent))
  } else {
    root.style.removeProperty('--accent')
    root.style.removeProperty('--accent-hover')
    root.style.removeProperty('--accent-contrast')
    root.style.removeProperty('--accent-soft')
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ThemeState>(loadStored)

  useEffect(() => {
    applyToDocument(state)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  }, [state])

  const setTheme = (theme: ThemeName) => setState((s) => ({ ...s, theme }))
  const setCustomAccent = (hex: string) => setState((s) => ({ ...s, theme: 'custom', customAccent: hex }))

  return (
    <ThemeContext.Provider value={{ ...state, setTheme, setCustomAccent }}>{children}</ThemeContext.Provider>
  )
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within a ThemeProvider')
  return ctx
}
