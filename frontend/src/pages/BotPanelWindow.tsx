import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { listSessions } from '../api/resources'
import { BotControlPanel } from '../components/BotControlPanel'
import { SoundboardPanel } from '../components/SoundboardPanel'

// Minimal view rendered in the detached Bot Control + Soundboard window (a
// real second Electron BrowserWindow - see electron/main.js:openBotPanelWindow
// and App.tsx's "/bot-panel" route). No sidebar/tabs - just the two panels a
// GM wants visible on a second monitor while running the main dashboard
// elsewhere.
export function BotPanelWindow() {
  const { token, user } = useAuth()
  const [latestSessionId, setLatestSessionId] = useState<number | null>(null)

  useEffect(() => {
    if (!token) return
    listSessions(token)
      .then((sessions) => {
        if (sessions.length > 0) setLatestSessionId(sessions[sessions.length - 1].id)
      })
      .catch(() => {})
  }, [token])

  if (!token || !user) {
    return (
      <div className="flex min-h-full items-center justify-center bg-[var(--bg)] p-6 text-center text-sm text-[var(--text-faint)]">
        Not logged in - log in from the main Lorekeeper window first.
      </div>
    )
  }

  return (
    <div className="min-h-full space-y-3 bg-[var(--bg)] p-3 text-[var(--text)]">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-faint)]">
        Bot Control &amp; Soundboard
      </h2>
      <BotControlPanel token={token} activeSessionId={latestSessionId} />
      <SoundboardPanel token={token} />
    </div>
  )
}
