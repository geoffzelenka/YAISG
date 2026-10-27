import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { type ActionFeedResponse, type Rewards } from '../../api/actions'
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
    cleanup()
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

  it('ignores zero-edge travel polls in toasts and the reward feed', async () => {
    const feed: ActionFeedResponse = {
      ...emptyActionResponse,
      active: activeFixture,
      since_last: {
        ...emptyActionResponse.since_last,
        details: {
          resolutions: [
            {
              edges_completed: [],
              supplies_used: {},
              xp: 0,
              current_realm_id: 'realm.verdant_vale',
              level_ups: {},
              stop_reason: null,
            },
          ],
        },
      },
    }
    mockFeed(feed)
    render(<ActionExperience />, { wrapper: actionWrapper })
    await screen.findByText('Journey step 1 of 1 · Current edge: road')
    expect(
      screen.getByRole('button', { name: 'Rewards (0)' }),
    ).toBeInTheDocument()
    expect(document.querySelector('[aria-live="polite"]')).toBeEmptyDOMElement()
    fireEvent.click(screen.getByRole('button', { name: 'Rewards (0)' }))
    expect(screen.getByText('No rewards received yet.')).toBeInTheDocument()
    expect(screen.queryByText('Action ended.')).not.toBeInTheDocument()
  })

  it('omits shared envelope fields from a uniform-cycle toast', async () => {
    mockFeed({
      ...emptyActionResponse,
      active: { ...activeFixture, meta: {} },
      since_last: {
        ...emptyActionResponse.since_last,
        cycles_completed: 1,
        xp_gained: { gathering: 10 },
        level_ups: { gathering: [2] },
        details: {
          resolutions: [{ level_ups: { gathering: [2] }, stop_reason: null }],
        },
      },
    })
    render(<ActionExperience />, { wrapper: actionWrapper })
    await screen.findByRole('button', { name: 'Rewards (1)' })
    const toast = document.querySelector('[aria-live="polite"]') as HTMLElement
    expect(
      within(toast).getByText(/gathering reached level 2/),
    ).toBeInTheDocument()
    expect(toast).not.toHaveTextContent('stop reason')
    expect(toast).not.toHaveTextContent('level ups')
    expect(toast).not.toHaveTextContent('Action ended.')
  })

  it.each([false, true])(
    'only uses the ended fallback when active is null: %s',
    async (ended) => {
      mockFeed({
        ...emptyActionResponse,
        active: ended ? null : activeFixture,
        since_last: {
          ...emptyActionResponse.since_last,
          details: { resolutions: [{ encounter: 'Ongoing encounter' }] },
        },
      })
      render(<ActionExperience />, { wrapper: actionWrapper })
      await screen.findByRole('button', { name: 'Rewards (1)' })
      const toast = document.querySelector(
        '[aria-live="polite"]',
      ) as HTMLElement
      await waitFor(() => expect(toast).toHaveTextContent('Ongoing encounter'))
      if (ended) expect(toast).toHaveTextContent('Action ended.')
      else expect(toast).not.toHaveTextContent('Action ended.')
    },
  )

  it('keeps polling after a failed request and prevents overlapping polls', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    let actionCalls = 0
    let resolveFirst: ((response: Response) => void) | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn((input: string | URL | Request) => {
        const path = new URL(String(input), 'http://test').pathname
        if (path === '/actions/poll') {
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

const activeFixture = {
  action_id: 'journey',
  cycle_ms: 60000,
  started_at: new Date().toISOString(),
  last_resolved_at: new Date().toISOString(),
  meta: { route: [{ edge_id: 'road' }], step_index: 0, remaining_ms: 50000 },
}

function mockFeed(feed: ActionFeedResponse) {
  vi.stubGlobal(
    'fetch',
    vi.fn((input: string | URL | Request) => {
      const path = new URL(String(input), 'http://test').pathname
      return Promise.resolve(
        jsonResponse(path === '/actions/poll' ? feed : contentBodies[path]),
      )
    }),
  )
}
