import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, within } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ContentProvider } from '../../api/content'
import type { CharacterProfile } from '../../api/characters'
import { startActionClock, useActionClock } from '../actions/actionStore'
import { MapPanel } from './MapPanel'
import { TransitionBanner } from './RealmPanel'

const contentBodies: Record<string, unknown> = {
  skills: { skills: [] },
  items: {
    items: [{ id: 'item.wood', name: 'Wood', stack_limit: 99, tags: [] }],
  },
  realms: {
    realms: [
      { id: 'realm.one', name: 'One', starting_node_id: 'node.one' },
      { id: 'realm.two', name: 'Two', starting_node_id: 'node.two' },
    ],
  },
  upgrades: { upgrades: [] },
  caps: {
    offline_hours: 12,
    inventory_slots: 30,
    order_slots: 5,
    key_listings: 2,
    belt_slots: 2,
  },
  map: { edges: [], positions: {} },
  estate_forms: { forms: [] },
  development: {
    nodes: [
      {
        id: 'node.two',
        realm_type: 'trade',
        name: 'New Harbor',
        inherent_tags: [],
        actions: [],
        modifiers: [],
        cap_bonuses: [],
        projects: [],
        tier: 1,
        carried_tags: [],
        upkeep: [],
        upgrades: [],
        regression: null,
      },
    ],
  },
  projects: { projects: [] },
  tags: { tags: [] },
  economy: {
    reserve_days: 3,
    cap_days: 11,
    warehouse_value_cap: 10000,
    coinage_multiple: 1.2,
    decay: { faltering_factor: 0.5 },
    transition: { duration_days: 7 },
    project: {
      idle_grace_days: 2,
      erosion_pct_per_day: 20,
      fail_cooldown_hours: 36,
    },
    tick: { per_day: 24, max_catchup: 72 },
  },
  progression: {
    visit_profile: {
      time_mult: 1,
      supply_mult: 1,
      terrains: ['land', 'water'],
    },
    travel_xp_per_second: 1,
    tier_benefits: {
      travel: [{ journey_speed_pct: 0, supply_reduction_pct: 0 }],
    },
    lint: { g: 1.015969, tolerance_pct: 15 },
    min_factor: 0.25,
    min_cycle_ms: 1,
    xp_bonus_cap_pct: 45,
    proficiency: {
      gathering: [0],
      refining: [0],
      manufacturing: [0],
      combat: [0],
      travel: [0],
      exploration: [0],
    },
    taper: {
      gathering: [1],
      refining: [1],
      manufacturing: [1],
      combat: [1],
      travel: [1],
      exploration: [1],
    },
    tier_thresholds: [1],
    tier_titles: ['Placeholder'],
  },
}

let client: QueryClient
function wrapper({ children }: PropsWithChildren) {
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ContentProvider>{children}</ContentProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

function response(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('realm client interactions', () => {
  beforeEach(() => {
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    localStorage.clear()
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('uses the shared 4 Hz clock and refetches transition state at expiry', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'))
    vi.stubGlobal(
      'fetch',
      vi.fn((input: string | URL | Request) => {
        const path = new URL(String(input), 'http://test').pathname
        if (path === '/estates/me')
          return Promise.resolve(
            response({ form: { mobility: 'fixed' }, realm_id: 'realm.one' }),
          )
        return Promise.resolve(
          response(
            path === '/content/manifest'
              ? { version: 'realm-test', packs: {} }
              : contentBodies[path.slice('/content/'.length)],
          ),
        )
      }),
    )
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    const stopClock = startActionClock()
    const view = render(
      <TransitionBanner
        realmId="realm.one"
        toNodeId="node.two"
        completesAt="2026-01-01T00:00:01Z"
      />,
      { wrapper },
    )
    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })
    expect(screen.getByText(/New Harbor/)).toBeInTheDocument()
    expect(screen.getByText('0:01')).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(1_000)
    })
    expect(useActionClock.getState().now).toBe(
      Date.parse('2026-01-01T00:00:01Z'),
    )
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ['realms', 'realm.one'],
    })
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ['characters', 'me', 'actions', 'available'],
    })

    act(() => {
      vi.advanceTimersByTime(1_000)
    })
    expect(invalidate).toHaveBeenCalledTimes(4)

    view.rerender(
      <TransitionBanner
        realmId="realm.one"
        toNodeId="node.two"
        completesAt="2026-01-01T00:00:03Z"
      />,
    )
    expect(screen.getByText('0:01')).toBeInTheDocument()
    act(() => {
      vi.advanceTimersByTime(1_000)
    })
    expect(invalidate).toHaveBeenCalledTimes(6)
    stopClock()
  })

  it('skips positionless map nodes and their edges without crashing', async () => {
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const path = new URL(String(input), 'http://test').pathname
      if (path === '/estates/me')
        return Promise.resolve(
          response({ form: { mobility: 'fixed' }, realm_id: 'realm.one' }),
        )
      if (path === '/content/manifest')
        return Promise.resolve(response({ version: 'map-test', packs: {} }))
      if (path.startsWith('/content/'))
        return Promise.resolve(
          response(contentBodies[path.slice('/content/'.length)]),
        )
      if (path.endsWith('/market'))
        return Promise.resolve(response({ lines: [] }))
      if (path === '/map')
        return Promise.resolve(
          response({
            nodes: [
              {
                realm_id: 'realm.one',
                name: 'One',
                position: { x: 100, y: 100 },
                gauge: 2.5,
              },
              { realm_id: 'realm.two', name: 'Two', position: null, gauge: 0 },
            ],
            edges: [
              {
                id: 'fake.edge',
                a: 'realm.one',
                b: 'realm.two',
                terrain: 'land',
                base_time_s: 60,
                supplies: [],
                min_travel_level: 1,
                base_loss_pct: 0,
                one_way: false,
              },
            ],
          }),
        )
      return Promise.resolve(response({}))
    })
    vi.stubGlobal('fetch', fetchMock)
    const profile = {
      character: { current_realm_id: 'realm.one' },
    } as CharacterProfile

    render(<MapPanel profile={profile} />, { wrapper })

    const graph = await screen.findByLabelText('Realm graph')
    const currentNode = within(graph).getByText('One')
    expect(currentNode.closest('g')?.querySelector('circle')).toHaveAttribute(
      'fill',
      '#34d399',
    )
    expect(
      within(screen.getByRole('list', { name: 'Realm health' })).getByText(
        /Gauge: 2.5 days/,
      ),
    ).toBeInTheDocument()
    expect(within(graph).queryByText('Two')).not.toBeInTheDocument()
    expect(within(graph).queryByTitle('land, 60s')).not.toBeInTheDocument()
  })
})
