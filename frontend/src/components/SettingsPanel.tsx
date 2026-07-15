import { useEffect, useState } from 'react'
import { getSettings, updateSettings } from '../api/resources'
import { encodeShareCode } from '../api/shareCode'
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
  const [passphrase, setPassphrase] = useState('')
  const [whisperModel, setWhisperModel] = useState('')
  const [summarizationModel, setSummarizationModel] = useState('')
  const [chunkMinutes, setChunkMinutes] = useState('')
  const [syncMinutes, setSyncMinutes] = useState('')

  const [shareCodePassphraseInput, setShareCodePassphraseInput] = useState('')
  const [shareCode, setShareCode] = useState('')
  const [copied, setCopied] = useState(false)

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
        campaign_passphrase: passphrase.trim() || undefined,
        whisper_model: whisperModel.trim() || undefined,
        summarization_model: summarizationModel.trim() || undefined,
        recording_chunk_minutes: chunkMinutes ? Number(chunkMinutes) : undefined,
        dndbeyond_sync_interval_minutes: syncMinutes ? Number(syncMinutes) : undefined,
      })
      setDiscordToken('')
      setOpenaiKey('')
      setPassphrase('')
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

      <div className="rounded-md border border-indigo-900 bg-indigo-950/40 p-3">
        <h4 className="mb-2 text-sm font-semibold text-slate-200">Play with others over the internet or LAN</h4>
        <p className="mb-2 text-xs text-slate-400">
          Traffic to this server is encrypted (HTTPS with a certificate your players' apps verify
          automatically via the share code below), so this is safe to use over the internet, not just
          your home network. To let players reach you from outside your network, forward TCP port{' '}
          <span className="font-mono text-slate-300">{settings.server_port}</span> to this computer in
          your router's settings - players on the same LAN don't need this step.
        </p>
        {settings.detected_public_ip && (
          <p className="mb-1 text-sm text-slate-300">
            Internet address: <span className="font-mono text-emerald-400">{settings.detected_public_ip}:{settings.server_port}</span>
          </p>
        )}
        {settings.detected_lan_ip && (
          <p className="mb-2 text-sm text-slate-300">
            LAN address: <span className="font-mono text-emerald-400">{settings.detected_lan_ip}:{settings.server_port}</span>
          </p>
        )}
        <label className="mb-1 block text-sm text-slate-400">
          Campaign Passphrase{' '}
          <span className={settings.campaign_passphrase_set ? 'text-emerald-400' : 'text-amber-400'}>
            ({settings.campaign_passphrase_set ? 'set' : 'not set - only this computer can log in'})
          </span>
        </label>
        <input
          type="password"
          value={passphrase}
          onChange={(e) => setPassphrase(e.target.value)}
          placeholder={settings.campaign_passphrase_set ? 'Leave blank to keep current passphrase' : 'Choose a passphrase'}
          className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500"
        />

        {settings.campaign_passphrase_set && (
          <div className="mt-3 border-t border-indigo-900/60 pt-3">
            <label className="mb-1 block text-sm text-slate-400">Generate a share code for your players</label>
            <div className="flex gap-2">
              <input
                type="password"
                value={shareCodePassphraseInput}
                onChange={(e) => setShareCodePassphraseInput(e.target.value)}
                placeholder="Re-enter your campaign passphrase"
                className="flex-1 rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500"
              />
              <button
                type="button"
                onClick={() => {
                  setShareCode(
                    encodeShareCode({
                      v: 1,
                      publicIp: settings.detected_public_ip,
                      lanIp: settings.detected_lan_ip,
                      port: settings.server_port,
                      passphrase: shareCodePassphraseInput.trim(),
                      fingerprint: settings.certificate_fingerprint,
                    }),
                  )
                  setCopied(false)
                }}
                disabled={!shareCodePassphraseInput.trim()}
                className="rounded-md border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-800 disabled:opacity-50"
              >
                Generate
              </button>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              We re-ask for the passphrase here because it's write-only - the server never sends it back.
            </p>
            {shareCode && (
              <div className="mt-2 space-y-1">
                <textarea
                  readOnly
                  value={shareCode}
                  rows={3}
                  className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 font-mono text-xs text-slate-300"
                  onFocus={(e) => e.target.select()}
                />
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(shareCode)
                      setCopied(true)
                    }}
                    className="rounded-md bg-indigo-600 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-500"
                  >
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                  <p className="text-xs text-slate-500">
                    Send this to your players - anyone with it can connect, so share it privately, not in a
                    public channel.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
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
