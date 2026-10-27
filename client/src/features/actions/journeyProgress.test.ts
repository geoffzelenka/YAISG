import { expect, it } from 'vitest'
import { journeyProgress } from './actionStore'

it('clamps at the current edge and snaps to a new server snapshot', () => {
  const resolved = '2026-01-01T00:00:00Z'
  const now = Date.parse(resolved)
  expect(journeyProgress(now, resolved, 10000, 4000)).toBe(0.6)
  expect(journeyProgress(now + 2000, resolved, 10000, 4000)).toBe(0.8)
  expect(journeyProgress(now + 20000, resolved, 10000, 4000)).toBe(1)
  expect(
    journeyProgress(
      now + 20000,
      new Date(now + 20000).toISOString(),
      20000,
      18000,
    ),
  ).toBe(0.1)
})
