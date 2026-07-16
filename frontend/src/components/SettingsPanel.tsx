import { useEffect, useState } from 'react'
import { getSettings, updateSettings } from '../api/resources'
import { encodeShareCode } from '../api/shareCode'
import { ThemePicker } from './ThemePicker'
import type { SettingsPublic } from '../types/api'

type Section = 'general' | 'ai' | 'networking'

// Maps a setup-<key> anchor (see SetupBanner) to whichever sub-tab actually
// contains it, so jumping here from outside Settings lands on the right
// section instead of just switching to Settings and leaving the GM to hunt.
const SETUP_KEY_TO_SECTION: Record<string, Section> = {
  discord_bot_token: 'general',
  openai_api_key: 'ai',
  ollama: 'ai',
  campaign_passphrase: 'networking',
}

// Secrets are write-only: the backend never echoes back a saved token/key,
// only whether one is set (see backend/app/routers/settings.py). The input
// stays blank on load and only gets sent if the GM types a new value.
export function SettingsPanel({ token, focusKey }: { token: string; focusKey?: string | null }) {
  const [settings, setSettings] = useState<SettingsPublic | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)
  const [section, setSection] = useState<Section>('general')

  const [discordToken, setDiscordToken] = useState('')
  const [openaiKey, setOpenaiKey] = useState('')
  const [passphrase, setPassphrase] = useState('')
  const [whisperModel, setWhisperModel] = useState('')
  const [summarizationModel, setSummarizationModel] = useState('')
  const [chunkMinutes, setChunkMinutes] = useState('')
  const [syncMinutes, setSyncMinutes] = useState('')
  const [showBotWalkthrough, setShowBotWalkthrough] = useState(false)
  const [showOpenaiWalkthrough, setShowOpenaiWalkthrough] = useState(false)
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

  useEffect(() => {
    if (focusKey && SETUP_KEY_TO_SECTION[focusKey]) {
      setSection(SETUP_KEY_TO_SECTION[focusKey])
    }
  }, [focusKey])

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

  if (!settings) return <p className="text-sm text-[var(--text-faint)]">Loading settings...</p>

  const SECTIONS: { key: Section; label: string }[] = [
    { key: 'general', label: 'General' },
    { key: 'ai', label: 'AI Providers' },
    { key: 'networking', label: 'Networking' },
  ]

  return (
    <form onSubmit={handleSubmit} className="max-w-3xl space-y-4 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
      <h3 className="text-lg font-semibold text-[var(--text)]">Settings</h3>
      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
      {saved && <p className="text-sm text-[var(--success)]">Saved.</p>}

      <div className="grid grid-cols-[150px_1fr] gap-6">
        <nav className="flex flex-col gap-1">
          {SECTIONS.map((s) => (
            <button
              key={s.key}
              type="button"
              onClick={() => setSection(s.key)}
              className={`rounded-md px-2.5 py-1.5 text-left text-sm ${
                section === s.key
                  ? 'bg-[var(--surface-2)] font-medium text-[var(--text)]'
                  : 'text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]'
              }`}
            >
              {s.label}
            </button>
          ))}
        </nav>

        <div className="min-w-0 space-y-4">
          {section === 'general' && (
            <>
              <div id="setup-discord_bot_token">
                <label className="mb-1 block text-sm text-[var(--text-muted)]">
                  Discord Bot Token{' '}
                  <span className={settings.discord_bot_token_set ? 'text-[var(--success)]' : 'text-[var(--text-faint)]'}>
                    ({settings.discord_bot_token_set ? 'set' : 'not set'}
                    {settings.discord_bot_token_set && ` - bot ${settings.bot_running ? 'running' : 'not running'}`})
                  </span>
                </label>
                <input
                  type="password"
                  value={discordToken}
                  onChange={(e) => setDiscordToken(e.target.value)}
                  placeholder={settings.discord_bot_token_set ? 'Leave blank to keep current token' : 'Paste your bot token'}
                  className="w-full rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)] placeholder-[var(--text-faint)]"
                />
                <button
                  type="button"
                  onClick={() => setShowBotWalkthrough((v) => !v)}
                  className="mt-1 text-xs text-[var(--accent)] hover:text-[var(--accent-hover)]"
                >
                  {showBotWalkthrough ? 'Hide' : "Don't have a bot yet? Show me how to make one"}
                </button>
                {showBotWalkthrough && (
                  <ol className="mt-2 list-decimal space-y-2 rounded-md border border-[var(--border)] bg-[var(--bg)] p-3 pl-7 text-xs text-[var(--text-muted)]">
                    <li>
                      Go to the{' '}
                      <a
                        href="https://discord.com/developers/applications"
                        target="_blank"
                        rel="noreferrer"
                        className="text-[var(--accent)] underline hover:text-[var(--accent-hover)]"
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
                <label className="mb-1 block text-sm text-[var(--text-muted)]">Appearance</label>
                <ThemePicker />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm text-[var(--text-muted)]">Recording chunk (minutes)</label>
                  <input
                    value={chunkMinutes}
                    onChange={(e) => setChunkMinutes(e.target.value.replace(/\D/g, ''))}
                    className="w-full rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)]"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-[var(--text-muted)]">D&D Beyond sync (minutes)</label>
                  <input
                    value={syncMinutes}
                    onChange={(e) => setSyncMinutes(e.target.value.replace(/\D/g, ''))}
                    className="w-full rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)]"
                  />
                </div>
              </div>
            </>
          )}

          {section === 'ai' && (
            <>
              <div id="setup-openai_api_key">
                <label className="mb-1 block text-sm text-[var(--text-muted)]">
                  OpenAI API Key{' '}
                  <span className={settings.openai_api_key_set ? 'text-[var(--success)]' : 'text-[var(--text-faint)]'}>
                    ({settings.openai_api_key_set ? 'set' : 'not set'})
                  </span>
                </label>
                <input
                  type="password"
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  placeholder={settings.openai_api_key_set ? 'Leave blank to keep current key' : 'sk-...'}
                  className="w-full rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)] placeholder-[var(--text-faint)]"
                />
                <p className="mt-1 text-xs text-[var(--text-faint)]">
                  Only needed if you use the OpenAI provider for transcription or summarization below - skip
                  this entirely if you're using local Whisper and Ollama for both.
                </p>
                <button
                  type="button"
                  onClick={() => setShowOpenaiWalkthrough((v) => !v)}
                  className="mt-1 text-xs text-[var(--accent)] hover:text-[var(--accent-hover)]"
                >
                  {showOpenaiWalkthrough ? 'Hide' : "Don't have a key yet? Show me how to make one"}
                </button>
                {showOpenaiWalkthrough && (
                  <ol className="mt-2 list-decimal space-y-2 rounded-md border border-[var(--border)] bg-[var(--bg)] p-3 pl-7 text-xs text-[var(--text-muted)]">
                    <li>
                      Create an account (or log in) at{' '}
                      <a
                        href="https://platform.openai.com/signup"
                        target="_blank"
                        rel="noreferrer"
                        className="text-[var(--accent)] underline hover:text-[var(--accent-hover)]"
                      >
                        platform.openai.com
                      </a>
                      . This is a separate account from ChatGPT's consumer plans - it's pay-as-you-go, billed
                      by usage.
                    </li>
                    <li>
                      Add a payment method under{' '}
                      <a
                        href="https://platform.openai.com/settings/organization/billing/overview"
                        target="_blank"
                        rel="noreferrer"
                        className="text-[var(--accent)] underline hover:text-[var(--accent-hover)]"
                      >
                        Billing
                      </a>
                      . A typical multi-hour session costs a few dollars in transcription + summarization.
                    </li>
                    <li>
                      Go to{' '}
                      <a
                        href="https://platform.openai.com/api-keys"
                        target="_blank"
                        rel="noreferrer"
                        className="text-[var(--accent)] underline hover:text-[var(--accent-hover)]"
                      >
                        API Keys
                      </a>
                      , click <strong>Create new secret key</strong>, and copy it immediately - OpenAI only
                      shows it once.
                    </li>
                    <li>Paste it into the field above and save.</li>
                  </ol>
                )}
              </div>

              <div className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] p-3">
                <h4 className="mb-1 text-sm font-semibold text-[var(--text)]">Transcription</h4>
                <p className="mb-2 text-xs text-[var(--text-muted)]">
                  Turns recorded voice into text. The OpenAI Whisper API costs a small amount per minute of
                  audio; the local option is completely free and keeps audio on this machine, at the cost of
                  slower processing and slightly lower accuracy.
                </p>
                <div className="mb-2 flex gap-4 text-sm text-[var(--text-muted)]">
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
                    <label className="mb-1 block text-sm text-[var(--text-muted)]">Whisper model</label>
                    <input
                      value={whisperModel}
                      onChange={(e) => setWhisperModel(e.target.value)}
                      className="w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-sm text-[var(--text)]"
                    />
                  </div>
                ) : (
                  <div>
                    <label className="mb-1 block text-sm text-[var(--text-muted)]">Local model size</label>
                    <select
                      value={localWhisperModelSize}
                      onChange={(e) => setLocalWhisperModelSize(e.target.value)}
                      className="w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-sm text-[var(--text)]"
                    >
                      <option value="tiny">Tiny - fastest, lowest accuracy (~75MB download)</option>
                      <option value="base">Base - fast, basic accuracy (~145MB download)</option>
                      <option value="small">Small - balanced, recommended (~480MB download)</option>
                      <option value="medium">Medium - slower, more accurate (~1.5GB download)</option>
                      <option value="large-v3">Large - slowest, most accurate (~3GB download)</option>
                    </select>
                    <p className="mt-1 text-xs text-[var(--text-faint)]">
                      The model downloads automatically the first time you process a session, then it's cached
                      on disk. No account or setup needed - this runs entirely on this computer.
                    </p>
                  </div>
                )}
              </div>

              <div id="setup-ollama" className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] p-3">
                <h4 className="mb-1 text-sm font-semibold text-[var(--text)]">Summarization</h4>
                <p className="mb-2 text-xs text-[var(--text-muted)]">
                  Turns the transcript into GM and player recaps. OpenAI's GPT-4o gives the highest quality
                  summaries but costs money per session; Ollama runs a free open-source model locally instead.
                </p>
                <div className="mb-2 flex gap-4 text-sm text-[var(--text-muted)]">
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
                  <p className="mb-2 text-xs text-[var(--text-muted)]">
                    Install{' '}
                    <a
                      href="https://ollama.com/download"
                      target="_blank"
                      rel="noreferrer"
                      className="text-[var(--accent)] underline hover:text-[var(--accent-hover)]"
                    >
                      Ollama
                    </a>
                    , then pull a model from a terminal, e.g. <code className="text-[var(--text-muted)]">ollama pull llama3.1</code>.
                    Ollama must be running in the background for summarization to work.
                  </p>
                )}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block text-sm text-[var(--text-muted)]">
                      {llmProvider === 'ollama' ? 'Ollama model name' : 'Summarization model'}
                    </label>
                    <input
                      value={summarizationModel}
                      onChange={(e) => setSummarizationModel(e.target.value)}
                      placeholder={llmProvider === 'ollama' ? 'llama3.1' : 'gpt-4o'}
                      className="w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-sm text-[var(--text)] placeholder-[var(--text-faint)]"
                    />
                  </div>
                  {llmProvider === 'ollama' && (
                    <div>
                      <label className="mb-1 block text-sm text-[var(--text-muted)]">Ollama URL</label>
                      <input
                        value={ollamaBaseUrl}
                        onChange={(e) => setOllamaBaseUrl(e.target.value)}
                        placeholder="http://localhost:11434/v1"
                        className="w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-sm text-[var(--text)] placeholder-[var(--text-faint)]"
                      />
                    </div>
                  )}
                </div>
              </div>
            </>
          )}

          {section === 'networking' && (
            <div className="rounded-md border border-[var(--accent)] bg-[var(--accent-soft)]/40 p-3">
              <h4 className="mb-2 text-sm font-semibold text-[var(--text)]">Play with others over the internet or LAN</h4>
              <p className="mb-2 text-xs text-[var(--text-muted)]">
                Traffic to this server is encrypted (HTTPS with a certificate your players' apps verify
                automatically via the share code below), so this is safe to use over the internet, not just
                your home network. Lorekeeper tries to open the port on your router automatically (UPnP)
                on launch; if your router doesn't support that, forward TCP port{' '}
                <span className="font-mono text-[var(--text-muted)]">{settings.server_port}</span> to this computer in
                your router's settings instead. Players on the same LAN don't need either step.
              </p>
              {settings.detected_public_ip && (
                <p className="mb-1 text-sm text-[var(--text-muted)]">
                  Internet address: <span className="font-mono text-[var(--success)]">{settings.detected_public_ip}:{settings.server_port}</span>
                </p>
              )}
              {settings.detected_lan_ip && (
                <p className="mb-2 text-sm text-[var(--text-muted)]">
                  LAN address: <span className="font-mono text-[var(--success)]">{settings.detected_lan_ip}:{settings.server_port}</span>
                </p>
              )}
              <label id="setup-campaign_passphrase" className="mb-1 block text-sm text-[var(--text-muted)]">
                Campaign Passphrase{' '}
                <span className={settings.campaign_passphrase_set ? 'text-[var(--success)]' : 'text-[var(--accent)]'}>
                  ({settings.campaign_passphrase_set ? 'set' : 'not set - only this computer can log in'})
                </span>
              </label>
              <input
                type="password"
                value={passphrase}
                onChange={(e) => setPassphrase(e.target.value)}
                placeholder={settings.campaign_passphrase_set ? 'Leave blank to keep current passphrase' : 'Choose a passphrase'}
                className="w-full rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)] placeholder-[var(--text-faint)]"
              />

              {settings.campaign_passphrase_set && (
                <div className="mt-3 border-t border-[var(--accent)]/60 pt-3">
                  <label className="mb-1 block text-sm text-[var(--text-muted)]">Generate a share code for your players</label>
                  <div className="flex gap-2">
                    <input
                      type="password"
                      value={shareCodePassphraseInput}
                      onChange={(e) => setShareCodePassphraseInput(e.target.value)}
                      placeholder="Re-enter your campaign passphrase"
                      className="flex-1 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)] placeholder-[var(--text-faint)]"
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
                      className="rounded-md border border-[var(--border)] px-3 py-1.5 text-sm hover:bg-[var(--surface-2)] disabled:opacity-50"
                    >
                      Generate
                    </button>
                  </div>
                  <p className="mt-1 text-xs text-[var(--text-faint)]">
                    We re-ask for the passphrase here because it's write-only - the server never sends it back.
                  </p>
                  {shareCode && (
                    <div className="mt-2 space-y-1">
                      <textarea
                        readOnly
                        value={shareCode}
                        rows={3}
                        className="w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-1.5 font-mono text-xs text-[var(--text-muted)]"
                        onFocus={(e) => e.target.select()}
                      />
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText(shareCode)
                            setCopied(true)
                          }}
                          className="rounded-md bg-[var(--accent)] px-3 py-1 text-xs font-medium text-white hover:bg-[var(--accent-hover)]"
                        >
                          {copied ? 'Copied!' : 'Copy'}
                        </button>
                        <p className="text-xs text-[var(--text-faint)]">
                          Send this to your players - anyone with it can connect, so share it privately, not in a
                          public channel.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <button
        type="submit"
        disabled={saving}
        className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50"
      >
        {saving ? 'Saving...' : 'Save settings'}
      </button>
    </form>
  )
}
