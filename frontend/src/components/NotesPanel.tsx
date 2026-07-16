import { useEffect, useState } from 'react'
import { createNote, listNotes } from '../api/resources'
import type { NotePublic, Role, UserPublic } from '../types/api'

interface Props {
  token: string
  sessionId: number
  role: Role
  players: UserPublic[] // used for the GM's "target player" picker and to label tagged notes
}

export function NotesPanel({ token, sessionId, role, players }: Props) {
  const [notes, setNotes] = useState<NotePublic[]>([])
  const [loading, setLoading] = useState(true)
  const [content, setContent] = useState('')
  const [isPrivate, setIsPrivate] = useState(false)
  const [targetPlayerId, setTargetPlayerId] = useState<number | ''>('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function playerName(userId: number): string | undefined {
    return players.find((p) => p.id === userId)?.username
  }

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
      <h4 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-faint)]">Notes</h4>

      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

      {loading ? (
        <p className="text-sm text-[var(--text-faint)]">Loading notes...</p>
      ) : notes.length === 0 ? (
        <p className="text-sm text-[var(--text-faint)]">No notes yet.</p>
      ) : (
        <ul className="space-y-2">
          {notes.map((note) => (
            <li
              key={note.id}
              className={`rounded-lg border px-3 py-2 text-sm ${
                note.is_private_gm
                  ? 'border-[var(--accent)] bg-[var(--accent-soft)]/40 text-[var(--text)]'
                  : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text)]'
              }`}
            >
              {note.is_private_gm ? (
                <div className="mb-1 text-xs uppercase tracking-wide text-[var(--accent)]">
                  Secret{note.target_player_id ? ' - shared with one player' : ' - GM only'}
                </div>
              ) : (
                note.target_player_id &&
                playerName(note.target_player_id) && (
                  <div className="mb-1 text-xs uppercase tracking-wide text-[var(--text-faint)]">
                    About {playerName(note.target_player_id)}
                  </div>
                )
              )}
              {note.content}
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleSubmit} className="space-y-2 border-t border-[var(--border)] pt-3">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Add a note..."
          rows={2}
          className="w-full rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text)] placeholder-[var(--text-faint)] focus:border-[var(--accent)] focus:outline-none"
        />
        {role === 'gm' && (
          <div className="flex flex-wrap items-center gap-3 text-sm text-[var(--text-muted)]">
            <label className="flex items-center gap-1.5">
              <input type="checkbox" checked={isPrivate} onChange={(e) => setIsPrivate(e.target.checked)} />
              Secret (GM only)
            </label>
            {/* Meaningful either way (Model B): when Secret, this scopes who
                can see it; when public, it's just an informational tag for
                who the note is about - so it must not be hidden behind the
                Secret checkbox. */}
            <select
              value={targetPlayerId}
              onChange={(e) => setTargetPlayerId(e.target.value ? Number(e.target.value) : '')}
              className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-[var(--text)]"
            >
              <option value="">{isPrivate ? 'GM only (no target player)' : 'Not about a specific player'}</option>
              {players.map((p) => (
                <option key={p.id} value={p.id}>
                  {isPrivate ? `Share with ${p.username}` : `About ${p.username}`}
                </option>
              ))}
            </select>
          </div>
        )}
        <button
          type="submit"
          disabled={submitting || !content.trim()}
          className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50"
        >
          {submitting ? 'Saving...' : 'Add note'}
        </button>
      </form>
    </div>
  )
}
