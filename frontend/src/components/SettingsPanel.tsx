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
  const [showBotWalkthrough, setShowBotWalkthrough] = useState(false)
  const [llmProvider, setLlmProvider] = useState<'openai' | 'ollama'>('openai')
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState('')
  const [transcriptionProvider, setTranscriptionProvider] = useState<'openai' | 'local'>('openai')
  const [localWhisperModelSize, setLocalWhisperModelSize] = useState('small')

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
      setLlmProvider(s.llm_provider === 'ollama' ? 'ollama' : 'openai')
      setOllamaBaseUrl(s.ollama_base_url)
      setTranscriptionProvider(s.transcription_provider === 'local' ? 'local' : 'openai')
      setLocalWhisperModelSize(s.local_whisper_model_size)
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
        llm_provider: llmProvider,
        ollama_base_url: ollamaBaseUrl.trim() || undefined,
        transcription_provider: transcriptionProvider,
        local_whisper_model_size: localWhisperModelSize,
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
        <button
          type="button"
          onClick={() => setShowBotWalkthrough((v) => !v)}
          className="mt-1 text-xs text-indigo-400 hover:text-indigo-300"
        >
          {showBotWalkthrough ? 'Hide' : "Don't have a bot yet? Show me how to make one"}
        </button>
        {showBotWalkthrough && (
          <ol className="mt-2 list-decimal space-y-2 rounded-md border border-slate-700 bg-slate-950 p-3 pl-7 text-xs text-slate-300">
            <li>
              Go to the{' '}
              <a
                href="https://discord.com/developers/applications"
                target="_blank"
                rel="noreferrer"
                className="text-indigo-400 underline hover:text-indigo-300"
              >
                Discord Developer Portal
              </a>
              , click <strong>New Application</strong>, and give it a name (e.g. "Lorekeeper").
            </li>
            <li>
              Open the <strong>Bot</strong> tab on the left. Click <strong>Reset Token</strong> (or{' '}
              <strong>Copy</strong> if one already exists) to get your bot token, then paste it into the
              field above.
            </li>
            <li>
              On the same Bot page, scroll to <strong>Privileged Gateway Intents</strong> and enable{' '}
              <strong>Server Members Intent</strong>. This is required for Lorekeeper to know who's in
              your voice channels.
            </li>
            <li>
              Open the <strong>OAuth2</strong> tab, then <strong>URL Generator</strong>. Under Scopes,
              check <strong>bot</strong> and <strong>applications.commands</strong>. Under Bot Permissions,
              check <strong>View Channels</strong>, <strong>Connect</strong>, and <strong>Speak</strong>.
            </li>
            <li>
              Copy the generated URL at the bottom of that page, open it in your browser, pick your
              server, and click <strong>Authorize</strong>. The bot will now appear in your server
              (offline until you paste its token here and save).
            </li>
          </ol>
        )}
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
          your home network. Lorekeeper tries to open the port on your router automatically (UPnP)
          on launch; if your router doesn't support that, forward TCP port{' '}
          <span className="font-mono text-slate-300">{settings.server_port}</span> to this computer in
          your router's settings instead. Players on the same LAN don't need either step.
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

      <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
        <h4 className="mb-1 text-sm font-semibold text-slate-200">Transcription</h4>
        <p className="mb-2 text-xs text-slate-400">
          Turns recorded voice into text. The OpenAI Whisper API costs a small amount per minute of
          audio; the local option is completely free and keeps audio on this machine, at the cost of
          slower processing and slightly lower accuracy.
        </p>
        <div className="mb-2 flex gap-4 text-sm text-slate-300">
          <label className="flex items-center gap-1.5">
            <input
              type="radio"
              checked={transcriptionProvider === 'openai'}
              onChange={() => setTranscriptionProvider('openai')}
            />
            OpenAI Whisper API (paid)
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="radio"
              checked={transcriptionProvider === 'local'}
              onChange={() => setTranscriptionProvider('local')}
            />
            Local Whisper (free)
          </label>
        </div>
        {transcriptionProvider === 'openai' ? (
          <div>
            <label className="mb-1 block text-sm text-slate-400">Whisper model</label>
            <input
              value={whisperModel}
              onChange={(e) => setWhisperModel(e.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100"
            />
          </div>
        ) : (
          <div>
            <label className="mb-1 block text-sm text-slate-400">Local model size</label>
            <select
              value={localWhisperModelSize}
              onChange={(e) => setLocalWhisperModelSize(e.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100"
            >
              <option value="tiny">Tiny - fastest, lowest accuracy (~75MB download)</option>
              <option value="base">Base - fast, basic accuracy (~145MB download)</option>
              <option value="small">Small - balanced, recommended (~480MB download)</option>
              <option value="medium">Medium - slower, more accurate (~1.5GB download)</option>
              <option value="large-v3">Large - slowest, most accurate (~3GB download)</option>
            </select>
            <p className="mt-1 text-xs text-slate-500">
              The model downloads automatically the first time you process a session, then it's cached
              on disk. No account or setup needed - this runs entirely on this computer.
            </p>
          </div>
        )}
      </div>

      <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
        <h4 className="mb-1 text-sm font-semibold text-slate-200">Summarization</h4>
        <p className="mb-2 text-xs text-slate-400">
          Turns the transcript into GM and player recaps. OpenAI's GPT-4o gives the highest quality
          summaries but costs money per session; Ollama runs a free open-source model locally instead.
        </p>
        <div className="mb-2 flex gap-4 text-sm text-slate-300">
          <label className="flex items-center gap-1.5">
            <input type="radio" checked={llmProvider === 'openai'} onChange={() => setLlmProvider('openai')} />
            OpenAI (paid)
          </label>
          <label className="flex items-center gap-1.5">
            <input type="radio" checked={llmProvider === 'ollama'} onChange={() => setLlmProvider('ollama')} />
            Ollama (free, local)
          </label>
        </div>
        {llmProvider === 'ollama' && (
          <p className="mb-2 text-xs text-slate-400">
            Install{' '}
            <a
              href="https://ollama.com/download"
              target="_blank"
              rel="noreferrer"
              className="text-indigo-400 underline hover:text-indigo-300"
            >
              Ollama
            </a>
            , then pull a model from a terminal, e.g. <code className="text-slate-300">ollama pull llama3.1</code>.
            Ollama must be running in the background for summarization to work.
          </p>
        )}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-sm text-slate-400">
              {llmProvider === 'ollama' ? 'Ollama model name' : 'Summarization model'}
            </label>
            <input
              value={summarizationModel}
              onChange={(e) => setSummarizationModel(e.target.value)}
              placeholder={llmProvider === 'ollama' ? 'llama3.1' : 'gpt-4o'}
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500"
            />
          </div>
          {llmProvider === 'ollama' && (
            <div>
              <label className="mb-1 block text-sm text-slate-400">Ollama URL</label>
              <input
                value={ollamaBaseUrl}
                onChange={(e) => setOllamaBaseUrl(e.target.value)}
                placeholder="http://localhost:11434/v1"
                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500"
              />
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
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
