import { useEffect, useRef } from 'react'

import { useActionClock } from '../actions/actionStore'
import { formatCountdown, remainingMilliseconds } from './countdownMath'

export function Countdown({
  completesAt,
  onExpire,
}: {
  completesAt: string
  onExpire: () => void
}) {
  const now = useActionClock((state) => state.now)
  const lastExpiryAttempt = useRef<number | null>(null)
  const remaining = remainingMilliseconds(now, completesAt)
  useEffect(() => {
    if (remaining > 0) {
      lastExpiryAttempt.current = null
      return
    }
    if (
      lastExpiryAttempt.current === null ||
      now - lastExpiryAttempt.current >= 1_000
    ) {
      lastExpiryAttempt.current = now
      onExpire()
    }
  }, [completesAt, now, onExpire, remaining])
  return <time dateTime={completesAt}>{formatCountdown(remaining)}</time>
}
