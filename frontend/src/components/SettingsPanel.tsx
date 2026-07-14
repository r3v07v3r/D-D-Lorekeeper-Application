import { useEffect, useState } from 'react'
import { getSettings, updateSettings } from '../api/resources'
import type { SettingsPublic } from '../types/api'

// Secrets are write-only: the backend never echoes back a saved token/key,
// only whether one is set (see backend/app/routers/settings.py). The input
// stays blank on load and only gets sent if the GM types a new value.
export function SettingsPanel({ token }: { token: string }) {
  const [settings, setSettings] = useState<SettingsPublic | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)

  const [discordToken, setDiscordToken] = useState('')
  const [openaiKey, setOpenaiKey] = useState('')
  const [whisperModel, setWhisperModel] = useState('')
  const [summarizationModel, setSummarizationModel] = useState('')
  const [chunkMinutes, setChunkMinutes] = useState('')
  const [syncMinutes, setSyncMinutes] = useState('')

  useEffect(() => {
    refresh()
  }, [])

  async function refresh() {
    try {
      const s = await getSettings(token)
      setSettings(s)
      setWhisperModel(s.whisper_model)
      setSummarizationModel(s.summarization_model)
      setChunkMinutes(String(s.recording_chunk_minutes))
      setSyncMinutes(String(s.dndbeyond_sync_interval_minutes))
      setError(null)
    } catch {
      setError('Could not load settings.')
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setSaved(false)
    try {
      await updateSettings(token, {
        discord_bot_token: discordToken.trim() || undefined,
        openai_api_key: openaiKey.trim() || undefined,
        whisper_model: whisperModel.trim() || undefined,
        summarization_model: summarizationModel.trim() || undefined,
        recording_chunk_minutes: chunkMinutes ? Number(chunkMinutes) : undefined,
        dndbeyond_sync_interval_minutes: syncMinutes ? Number(syncMinutes) : undefined,
      })
      setDiscordToken('')
      setOpenaiKey('')
      await refresh()
      setSaved(true)
      setError(null)
    } catch {
      setError('Could not save settings.')
    } finally {
      setSaving(false)
    }
  }

  if (!settings) return <p className="text-sm text-slate-500">Loading settings...</p>

  return (
    <form onSubmit={handleSubmit} className="max-w-lg space-y-4 rounded-lg border border-slate-800 bg-slate-900 p-4">
      <h3 className="text-lg font-semibold text-slate-100">Settings</h3>
      {error && <p className="text-sm text-red-400">{error}</p>}
      {saved && <p className="text-sm text-emerald-400">Saved.</p>}

      <div>
        <label className="mb-1 block text-sm text-slate-400">
          Discord Bot Token{' '}
          <span className={settings.discord_bot_token_set ? 'text-emerald-400' : 'text-slate-500'}>
            ({settings.discord_bot_token_set ? 'set' : 'not set'}
            {settings.discord_bot_token_set && ` - bot ${settings.bot_running ? 'running' : 'not running'}`})
          </span>
        </label>
        <input
          type="password"
          value={discordToken}
          onChange={(e) => setDiscordToken(e.target.value)}
          placeholder={settings.discord_bot_token_set ? 'Leave blank to keep current token' : 'Paste your bot token'}
          className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm text-slate-400">
          OpenAI API Key{' '}
          <span className={settings.openai_api_key_set ? 'text-emerald-400' : 'text-slate-500'}>
            ({settings.openai_api_key_set ? 'set' : 'not set'})
          </span>
        </label>
        <input
          type="password"
          value={openaiKey}
          onChange={(e) => setOpenaiKey(e.target.value)}
          placeholder={settings.openai_api_key_set ? 'Leave blank to keep current key' : 'sk-...'}
          className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-sm text-slate-400">Whisper model</label>
          <input
            value={whisperModel}
            onChange={(e) => setWhisperModel(e.target.value)}
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-slate-400">Summarization model</label>
          <input
            value={summarizationModel}
            onChange={(e) => setSummarizationModel(e.target.value)}
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-slate-400">Recording chunk (minutes)</label>
          <input
            value={chunkMinutes}
            onChange={(e) => setChunkMinutes(e.target.value.replace(/\D/g, ''))}
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-slate-400">D&D Beyond sync (minutes)</label>
          <input
            value={syncMinutes}
            onChange={(e) => setSyncMinutes(e.target.value.replace(/\D/g, ''))}
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={saving}
        className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
      >
        {saving ? 'Saving...' : 'Save settings'}
      </button>
    </form>
  )
}
