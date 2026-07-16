import { useEffect, useRef, useState } from 'react'
import {
  deleteSoundClip,
  getBotStatus,
  getSoundClipAudio,
  listSoundClips,
  playSoundClip,
  stopSoundClip,
  updateSoundClip,
  uploadSoundClip,
} from '../api/resources'
import type { BotStatusResponse, SoundClipPublic } from '../types/api'

type PlaybackMode = 'bot' | 'speakers'

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      // reader.result is a data: URL ("data:audio/mpeg;base64,AAAA...") -
      // only the part after the comma is the base64 payload itself.
      resolve(result.slice(result.indexOf(',') + 1))
    }
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}

export function SoundboardPanel({ token }: { token: string }) {
  const [clips, setClips] = useState<SoundClipPublic[]>([])
  const [botStatus, setBotStatus] = useState<BotStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [busyClipId, setBusyClipId] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [pendingName, setPendingName] = useState('')
  // "speakers" plays the clip locally through this computer's own audio
  // output instead of relaying it through the bot - useful with no bot
  // configured yet, or for a GM who'd rather it ride along on their own open
  // mic/Discord call the way playing music from a phone near a mic already
  // works, just automated. Defaults to speakers when there's no bot
  // connected yet, since "bot" mode cannot work at all in that state.
  const [playbackMode, setPlaybackMode] = useState<PlaybackMode>('bot')
  const modeInitialized = useRef(false)
  const localAudioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    refresh()
    refreshBotStatus()
    // "Connected" here means the bot itself has joined a channel (from Bot
    // Control) - not whether you personally are in one - so this needs to
    // stay live rather than a one-time check, since it's easy to change
    // from the other tab and forget.
    const interval = setInterval(refreshBotStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  async function refresh() {
    try {
      setClips(await listSoundClips(token))
      setError(null)
    } catch {
      setError('Could not load soundboard clips.')
    }
  }

  async function refreshBotStatus() {
    try {
      const status = await getBotStatus(token)
      setBotStatus(status)
      // Picks a sensible starting mode once, based on whether the bot is
      // usable at all - never overrides a GM's own choice on later polls.
      if (!modeInitialized.current) {
        modeInitialized.current = true
        setPlaybackMode(status.connected ? 'bot' : 'speakers')
      }
    } catch {
      // Bot Control tab already surfaces connection errors - avoid a
      // redundant/competing error message here.
    }
  }

  async function handleFileChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const content_base64 = await fileToBase64(file)
      await uploadSoundClip(token, {
        name: pendingName.trim() || file.name.replace(/\.[^.]+$/, ''),
        filename: file.name,
        content_base64,
      })
      setPendingName('')
      if (fileInputRef.current) fileInputRef.current.value = ''
      await refresh()
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not upload that file.')
    } finally {
      setUploading(false)
    }
  }

  async function handlePlay(clip: SoundClipPublic) {
    setBusyClipId(clip.id)
    try {
      if (playbackMode === 'speakers') {
        const { content_base64, mime_type } = await getSoundClipAudio(token, clip.id)
        const bytes = Uint8Array.from(atob(content_base64), (c) => c.charCodeAt(0))
        const url = URL.createObjectURL(new Blob([bytes], { type: mime_type }))
        const audio = localAudioRef.current
        if (audio) {
          audio.src = url
          // HTML5 <audio> only goes up to 1.0; the volume slider allows up
          // to 1.5 for bot playback, which mixes into a full Discord voice
          // stream rather than a single local output device.
          audio.volume = Math.min(clip.volume, 1)
          await audio.play()
        }
      } else {
        await playSoundClip(token, clip.id)
      }
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not play that clip.')
    } finally {
      setBusyClipId(null)
    }
  }

  async function handleStop() {
    try {
      if (localAudioRef.current) {
        localAudioRef.current.pause()
        localAudioRef.current.currentTime = 0
      }
      await stopSoundClip(token)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nothing was playing.')
    }
  }

  async function handleVolumeChange(clip: SoundClipPublic, volume: number) {
    setClips((prev) => prev.map((c) => (c.id === clip.id ? { ...c, volume } : c)))
    try {
      await updateSoundClip(token, clip.id, { volume })
    } catch {
      setError('Could not save volume.')
    }
  }

  async function handleDelete(clipId: number) {
    setBusyClipId(clipId)
    try {
      await deleteSoundClip(token, clipId)
      await refresh()
    } catch {
      setError('Could not delete that clip.')
    } finally {
      setBusyClipId(null)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-[var(--text)]">Soundboard</h3>
        <button
          onClick={handleStop}
          className="rounded-md border border-[var(--danger)] px-3 py-1.5 text-sm text-[var(--danger)] hover:bg-[var(--danger-soft)]"
        >
          Stop playback
        </button>
      </div>

      <div className="flex items-center gap-2 text-sm">
        <span className="text-[var(--text-faint)]">Play through</span>
        <div className="inline-flex overflow-hidden rounded-md border border-[var(--border)]">
          <button
            onClick={() => setPlaybackMode('bot')}
            className={
              'px-3 py-1 ' +
              (playbackMode === 'bot'
                ? 'bg-[var(--accent)] text-white'
                : 'bg-[var(--surface)] text-[var(--text-muted)] hover:bg-[var(--surface-2)]')
            }
          >
            Discord bot
          </button>
          <button
            onClick={() => setPlaybackMode('speakers')}
            className={
              'px-3 py-1 ' +
              (playbackMode === 'speakers'
                ? 'bg-[var(--accent)] text-white'
                : 'bg-[var(--surface)] text-[var(--text-muted)] hover:bg-[var(--surface-2)]')
            }
          >
            My speakers
          </button>
        </div>
      </div>
      <p className="text-xs text-[var(--text-faint)]">
        {playbackMode === 'bot'
          ? 'Sounds play into the Discord voice channel through the bot.'
          : "Sounds play out loud on this computer, riding along on your own open mic/call the same way playing music from a phone near a mic would."}{' '}
        Supported formats: mp3, wav, ogg, m4a, flac (max 8MB each).
      </p>

      {playbackMode === 'bot' && botStatus && !botStatus.connected && (
        <div className="rounded-md border border-[var(--accent)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm text-[var(--accent)]">
          The <strong>bot</strong> hasn't joined a voice channel yet - being in the channel yourself
          isn't enough, the bot needs to join too. Go to <strong>Bot Control</strong> and click Join,
          or switch to <strong>My speakers</strong> above.
        </div>
      )}

      <audio ref={localAudioRef} className="hidden" />

      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

      <div className="flex gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
        <input
          value={pendingName}
          onChange={(e) => setPendingName(e.target.value)}
          placeholder="Clip name (optional - defaults to filename)"
          className="flex-1 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)] placeholder-[var(--text-faint)]"
        />
        <input
          ref={fileInputRef}
          type="file"
          accept=".mp3,.wav,.ogg,.m4a,.flac,audio/*"
          onChange={handleFileChosen}
          disabled={uploading}
          className="text-sm text-[var(--text-muted)] file:mr-3 file:rounded-md file:border-0 file:bg-[var(--accent)] file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-white hover:file:bg-[var(--accent-hover)]"
        />
      </div>

      {clips.length === 0 ? (
        <p className="text-sm text-[var(--text-faint)]">No clips uploaded yet.</p>
      ) : (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {clips.map((clip) => (
            <div key={clip.id} className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="truncate font-medium text-[var(--text)]">{clip.name}</span>
                <button
                  onClick={() => handleDelete(clip.id)}
                  disabled={busyClipId === clip.id}
                  className="text-xs text-[var(--text-faint)] hover:text-[var(--danger)] disabled:opacity-50"
                >
                  Delete
                </button>
              </div>
              <button
                onClick={() => handlePlay(clip)}
                disabled={busyClipId === clip.id || (playbackMode === 'bot' && !botStatus?.connected)}
                title={
                  playbackMode === 'bot' && !botStatus?.connected
                    ? 'The bot needs to join a voice channel first (Bot Control tab), or switch to My speakers above'
                    : undefined
                }
                className="mb-2 w-full rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50"
              >
                {busyClipId === clip.id ? 'Playing...' : 'Play'}
              </button>
              <label className="flex items-center gap-2 text-xs text-[var(--text-faint)]">
                Volume
                <input
                  type="range"
                  min={0}
                  max={1.5}
                  step={0.05}
                  value={clip.volume}
                  onChange={(e) => handleVolumeChange(clip, Number(e.target.value))}
                  className="flex-1"
                />
                <span className="w-10 text-right">{Math.round(clip.volume * 100)}%</span>
              </label>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
