import { useEffect, useState } from 'react'
import { createCampaign, listCampaigns, setActiveCampaign } from '../api/resources'
import type { CampaignPublic } from '../types/api'

// Shown before the rest of the GM dashboard whenever no campaign is active
// yet - either a fresh install, or the GM explicitly chose to switch. Picking
// or creating a campaign here is what makes it "active" (see
// backend/app/routers/campaigns.py), which is also what any connected
// players see - there's no separate per-player campaign picker.
export function CampaignPicker({
  token,
  onSelected,
  onCancel,
}: {
  token: string
  onSelected: (campaign: CampaignPublic) => void
  onCancel?: () => void
}) {
  const [campaigns, setCampaigns] = useState<CampaignPublic[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    refresh()
  }, [])

  async function refresh() {
    try {
      setCampaigns(await listCampaigns(token))
      setError(null)
    } catch {
      setError('Could not load campaigns.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSelect(campaign: CampaignPublic) {
    setBusy(true)
    try {
      await setActiveCampaign(token, campaign.id)
      onSelected(campaign)
    } catch {
      setError('Could not select that campaign.')
    } finally {
      setBusy(false)
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!newName.trim()) return
    setBusy(true)
    try {
      const campaign = await createCampaign(token, newName.trim())
      await setActiveCampaign(token, campaign.id)
      onSelected(campaign)
    } catch {
      setError('Could not create that campaign.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4 py-10">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-[var(--text)]">Choose a campaign</h2>
          <p className="text-sm text-[var(--text-faint)]">
            {campaigns.length > 0
              ? 'Select which campaign you are running, or start a new one.'
              : 'Give your campaign a name to get started - everything else can change later.'}
          </p>
        </div>
        {onCancel && (
          <button type="button" onClick={onCancel} className="text-sm text-[var(--text-faint)] hover:text-[var(--text)]">
            Cancel
          </button>
        )}
      </div>

      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

      {loading ? (
        <p className="text-sm text-[var(--text-faint)]">Loading...</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {campaigns.map((c) => (
            <button
              key={c.id}
              type="button"
              disabled={busy}
              onClick={() => handleSelect(c)}
              className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 text-left hover:border-[var(--accent)] disabled:opacity-50"
            >
              <div className="font-medium text-[var(--text)]">{c.name}</div>
              <div className="mt-1 text-xs text-[var(--text-faint)]">
                Created {new Date(c.created_at).toLocaleDateString()}
              </div>
            </button>
          ))}

          <button
            type="button"
            disabled={busy}
            onClick={() => setCreating(true)}
            className="flex min-h-20 items-center justify-center rounded-lg border border-dashed border-[var(--border)] p-4 text-sm text-[var(--text-faint)] hover:border-[var(--accent)] hover:text-[var(--text)] disabled:opacity-50"
          >
            + New Campaign
          </button>
        </div>
      )}

      {creating && (
        <form onSubmit={handleCreate} className="flex gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Campaign name"
            className="flex-1 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)] placeholder-[var(--text-faint)]"
          />
          <button
            type="submit"
            disabled={busy || !newName.trim()}
            className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50"
          >
            Create
          </button>
        </form>
      )}
    </div>
  )
}
