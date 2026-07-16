// Formats a count of seconds as a short human-readable duration for the
// Home dashboard's "time in Lorekeeper" stats (see User.total_seconds_active).
export function formatDuration(totalSeconds: number): string {
  if (totalSeconds < 60) return '< 1m'
  const totalMinutes = Math.floor(totalSeconds / 60)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours === 0) return `${minutes}m`
  return `${hours}h ${minutes}m`
}
