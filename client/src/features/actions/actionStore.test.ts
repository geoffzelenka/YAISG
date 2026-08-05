import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  cycleProgress,
  nextCycleDelay,
  startActionClock,
  useActionClock,
} from './actionStore'

describe('action timing', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('calculates cosmetic progress from started_at', () => {
    expect(
      cycleProgress(
        Date.parse('2026-01-01T00:00:04Z'),
        '2026-01-01T00:00:00Z',
        10_000,
      ),
    ).toBe(0.4)
    expect(
      cycleProgress(
        Date.parse('2026-01-01T00:00:14Z'),
        '2026-01-01T00:00:00Z',
        10_000,
      ),
    ).toBe(0.4)
  })

  it('drives all subscribers from one four-times-per-second clock', () => {
    vi.useFakeTimers()
    vi.setSystemTime(1_000)
    const stopOne = startActionClock()
    const stopTwo = startActionClock()
    vi.advanceTimersByTime(250)
    expect(useActionClock.getState().now).toBe(1_250)
    expect(vi.getTimerCount()).toBe(1)
    stopOne()
    stopTwo()
  })

  it('schedules polling at a cycle boundary with bounded jitter', () => {
    const started = '2026-01-01T00:00:00Z'
    const now = Date.parse('2026-01-01T00:00:07Z')
    expect(nextCycleDelay(now, started, 5_000, () => 0)).toBe(2_500)
    expect(nextCycleDelay(now, started, 5_000, () => 1)).toBe(3_500)
  })
})
