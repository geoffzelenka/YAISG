export function remainingMilliseconds(
  now: number,
  completesAt: string,
): number {
  return Math.max(0, Date.parse(completesAt) - now)
}

export function formatCountdown(milliseconds: number): string {
  const seconds = Math.ceil(milliseconds / 1000)
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainder = seconds % 60
  return hours > 0
    ? `${hours}:${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`
    : `${minutes}:${String(remainder).padStart(2, '0')}`
}
