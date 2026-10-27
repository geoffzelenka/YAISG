import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { type Rewards } from '../../api/actions'
import { ContentProvider } from '../../api/content'
import { ActionExperience, WelcomeBack } from './ActionExperience'
import { shouldShowWelcomeBack } from './rewardPresentation'

const rewards: Rewards = {
  cycles_completed: 8,
  xp_gained: { gathering: 80 },
  items_consumed: {},
  items_gained: { 'item.fake_sprig': 8 },
  overflowed_items: {},
  level_ups: {},
  stop_reason: 'offline_cap',
}

describe('welcome-back summary', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('triggers only when since_last spans more than five cycles', () => {
    expect(shouldShowWelcomeBack(rewards)).toBe(true)
    expect(shouldShowWelcomeBack({ ...rewards, cycles_completed: 5 })).toBe(
      false,
    )
  })

  it('shows authoritative offline gains and stop reason', () => {
    let closed = false
    render(
      <WelcomeBack
        rewards={rewards}
        onClose={() => {
          closed = true
        }}
      />,
    )
    expect(screen.getByRole('dialog')).toHaveTextContent('8 cycles completed')
    expect(screen.getByRole('dialog')).toHaveTextContent('gathering XP: 80')
    expect(screen.getByRole('dialog')).toHaveTextContent('offline cap')
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
    expect(closed).toBe(true)
  })

  it('keeps polling after a failed request and prevents overlapping polls', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    let actionCalls = 0
    let resolveFirst: ((response: Response) => void) | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn((input: string | URL | Request) => {
        const path = new URL(String(input), 'http://test').pathname
        if (path === '/characters/me/action') {
          actionCalls += 1
          if (actionCalls === 1) {
            return new Promise<Response>((resolve) => {
              resolveFirst = resolve
            })
          }
          return Promise.resolve(jsonResponse(emptyActionResponse))
        }
        return Promise.resolve(jsonResponse(contentBodies[path]))
      }),
    )
    render(<ActionExperience />, { wrapper: actionWrapper })
    await vi.waitFor(() => expect(actionCalls).toBe(1))
    window.dispatchEvent(new Event('focus'))
    window.dispatchEvent(new Event('online'))
    expect(actionCalls).toBe(1)
    resolveFirst?.(
      new Response(JSON.stringify({ error: { message: 'Offline' } }), {
        status: 503,
      }),
    )
    await vi.advanceTimersByTimeAsync(30_000)
    await vi.waitFor(() => expect(actionCalls).toBe(2))
  })
})

const emptyActionResponse = {
  active: null,
  since_last: {
    cycles_completed: 0,
    xp_gained: {},
    items_consumed: {},
    items_gained: {},
    overflowed_items: {},
    level_ups: {},
    stop_reason: null,
  },
  stop_reason: null,
}

const contentBodies: Record<string, unknown> = {
  '/content/manifest': { version: 'poll-test', packs: {} },
  '/content/skills': { skills: [] },
  '/content/items': { items: [] },
  '/content/realms': { realms: [] },
  '/content/upgrades': { upgrades: [] },
  '/content/caps': {
    offline_hours: 12,
    inventory_slots: 30,
    order_slots: 5,
    key_listings: 2,
    belt_slots: 2,
    estate_upgrade_slots: 2,
  },
}

function jsonResponse(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

function actionWrapper({ children }: PropsWithChildren) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return (
    <QueryClientProvider client={client}>
      <ContentProvider>{children}</ContentProvider>
    </QueryClientProvider>
  )
}
