import { useEffect, useRef, useState } from 'react'
import { deleteSoundClip, listSoundClips, playSoundClip, stopSoundClip, updateSoundClip, uploadSoundClip } from '../api/resources'
import type { SoundClipPublic } from '../types/api'

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
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [busyClipId, setBusyClipId] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [pendingName, setPendingName] = useState('')

  useEffect(() => {
    refresh()
  }, [])

  async function refresh() {
    try {
      setClips(await listSoundClips(token))
      setError(null)
    } catch {
      setError('Could not load soundboard clips.')
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

  async function handlePlay(clipId: number) {
    setBusyClipId(clipId)
    try {
      await playSoundClip(token, clipId)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not play that clip.')
    } finally {
      setBusyClipId(null)
    }
  }

  async function handleStop() {
    try {
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
        <h3 className="text-lg font-semibold text-slate-100">Soundboard</h3>
        <button
          onClick={handleStop}
          className="rounded-md border border-red-800 px-3 py-1.5 text-sm text-red-300 hover:bg-red-950"
        >
          Stop playback
        </button>
      </div>
      <p className="text-xs text-slate-500">
        Sounds play into the connected Discord voice channel via the bot - join a channel in Bot Control
        first. Supported formats: mp3, wav, ogg, m4a, flac (max 8MB each).
      </p>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="flex gap-2 rounded-lg border border-slate-800 bg-slate-900 p-3">
        <input
          value={pendingName}
          onChange={(e) => setPendingName(e.target.value)}
          placeholder="Clip name (optional - defaults to filename)"
          className="flex-1 rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500"
        />
        <input
          ref={fileInputRef}
          type="file"
          accept=".mp3,.wav,.ogg,.m4a,.flac,audio/*"
          onChange={handleFileChosen}
          disabled={uploading}
          className="text-sm text-slate-300 file:mr-3 file:rounded-md file:border-0 file:bg-indigo-600 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-white hover:file:bg-indigo-500"
        />
      </div>

      {clips.length === 0 ? (
        <p className="text-sm text-slate-500">No clips uploaded yet.</p>
      ) : (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {clips.map((clip) => (
            <div key={clip.id} className="rounded-lg border border-slate-800 bg-slate-900 p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="truncate font-medium text-slate-100">{clip.name}</span>
                <button
                  onClick={() => handleDelete(clip.id)}
                  disabled={busyClipId === clip.id}
                  className="text-xs text-slate-500 hover:text-red-400 disabled:opacity-50"
                >
                  Delete
                </button>
              </div>
              <button
                onClick={() => handlePlay(clip.id)}
                disabled={busyClipId === clip.id}
                className="mb-2 w-full rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
              >
                {busyClipId === clip.id ? 'Playing...' : 'Play'}
              </button>
              <label className="flex items-center gap-2 text-xs text-slate-500">
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
