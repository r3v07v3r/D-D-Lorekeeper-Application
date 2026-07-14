import { useEffect, useState } from 'react'
import { createNote, listNotes } from '../api/resources'
import type { NotePublic, Role, UserPublic } from '../types/api'

interface Props {
  token: string
  sessionId: number
  role: Role
  players: UserPublic[] // only used to populate the GM's "target player" picker
}

export function NotesPanel({ token, sessionId, role, players }: Props) {
  const [notes, setNotes] = useState<NotePublic[]>([])
  const [loading, setLoading] = useState(true)
  const [content, setContent] = useState('')
  const [isPrivate, setIsPrivate] = useState(false)
  const [targetPlayerId, setTargetPlayerId] = useState<number | ''>('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    refresh()
  }, [sessionId])

  async function refresh() {
    setLoading(true)
    try {
      setNotes(await listNotes(token, sessionId))
      setError(null)
    } catch {
      setError('Could not load notes.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!content.trim()) return
    setSubmitting(true)
    try {
      await createNote(token, sessionId, {
        content: content.trim(),
        is_private_gm: role === 'gm' ? isPrivate : false,
        target_player_id: role === 'gm' && targetPlayerId !== '' ? targetPlayerId : null,
      })
      setContent('')
      setIsPrivate(false)
      setTargetPlayerId('')
      await refresh()
    } catch {
      setError('Could not create note.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Notes</h4>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {loading ? (
        <p className="text-sm text-slate-500">Loading notes...</p>
      ) : notes.length === 0 ? (
        <p className="text-sm text-slate-500">No notes yet.</p>
      ) : (
        <ul className="space-y-2">
          {notes.map((note) => (
            <li
              key={note.id}
              className={`rounded-lg border px-3 py-2 text-sm ${
                note.is_private_gm
                  ? 'border-amber-800 bg-amber-950/40 text-amber-100'
                  : 'border-slate-800 bg-slate-900 text-slate-200'
              }`}
            >
              {note.is_private_gm && (
                <div className="mb-1 text-xs uppercase tracking-wide text-amber-400">
                  Secret{note.target_player_id ? ' - shared with one player' : ' - GM only'}
                </div>
              )}
              {note.content}
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleSubmit} className="space-y-2 border-t border-slate-800 pt-3">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Add a note..."
          rows={2}
          className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
        />
        {role === 'gm' && (
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-400">
            <label className="flex items-center gap-1.5">
              <input type="checkbox" checked={isPrivate} onChange={(e) => setIsPrivate(e.target.checked)} />
              Secret (GM only)
            </label>
            {isPrivate && (
              <select
                value={targetPlayerId}
                onChange={(e) => setTargetPlayerId(e.target.value ? Number(e.target.value) : '')}
                className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1 text-slate-100"
              >
                <option value="">GM only (no target player)</option>
                {players.map((p) => (
                  <option key={p.id} value={p.id}>
                    Share with {p.username}
                  </option>
                ))}
              </select>
            )}
          </div>
        )}
        <button
          type="submit"
          disabled={submitting || !content.trim()}
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {submitting ? 'Saving...' : 'Add note'}
        </button>
      </form>
    </div>
  )
}
