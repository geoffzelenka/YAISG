import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ContentProvider } from '../../api/content'
import type { CharacterProfile } from '../../api/characters'
import { startActionClock, useActionClock } from '../actions/actionStore'
import { MapPanel } from './MapPanel'
import { PendingRelocationBanner } from './PendingRelocationBanner'
import { ContributionForm, TransitionBanner } from './RealmPanel'
import { RelocationFlow } from './RelocationFlow'

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
    estate_upgrade_slots: 2,
  },
  map: { edges: [], positions: {} },
  estate_forms: { forms: [], transformations: [], relocation_classes: {} },
  development: {
    nodes: [
      {
        id: 'node.two',
        archetype: 'trade',
        name: 'New Harbor',
        inherent_tags: [],
        actions: [],
        modifiers: [],
        cap_bonuses: [],
        projects: [],
      },
    ],
    edges: [],
  },
  projects: { projects: [] },
  tags: { tags: [] },
  economy: { decay: { faltering_factor: 0.5 } },
  progression: {
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
      <ContentProvider>{children}</ContentProvider>
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
      if (path === '/content/manifest')
        return Promise.resolve(response({ version: 'map-test', packs: {} }))
      if (path.startsWith('/content/'))
        return Promise.resolve(
          response(contentBodies[path.slice('/content/'.length)]),
        )
      if (path === '/map')
        return Promise.resolve(
          response({
            nodes: [
              {
                realm_id: 'realm.one',
                name: 'One',
                position: { x: 100, y: 100 },
              },
              { realm_id: 'realm.two', name: 'Two', position: null },
            ],
            edges: [
              {
                realms: ['realm.one', 'realm.two'],
                cost: { gold: 25, items: [], time_ms: 60000 },
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

    const currentNode = await screen.findByText('One')
    expect(currentNode.closest('g')?.querySelector('circle')).toHaveAttribute(
      'fill',
      '#34d399',
    )
    const graph = screen.getByLabelText('Realm graph')
    expect(within(graph).queryByText('Two')).not.toBeInTheDocument()
    expect(within(graph).queryByTitle('25 gold, 60s')).not.toBeInTheDocument()
  })

  it('shows pending relocation and retries profile invalidation after expiry', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'))
    vi.stubGlobal(
      'fetch',
      vi.fn((input: string | URL | Request) => {
        const path = new URL(String(input), 'http://test').pathname
        if (path === '/content/manifest')
          return Promise.resolve(
            response({ version: 'banner-test', packs: {} }),
          )
        if (path.startsWith('/content/'))
          return Promise.resolve(
            response(contentBodies[path.slice('/content/'.length)]),
          )
        return Promise.resolve(
          response({
            id: 'estate.one',
            form: {},
            realm_id: 'realm.one',
            level: 1,
            status: 'relocating',
            upgrade_slots: 2,
            installed_upgrades: [],
            relocating_to_realm_id: 'realm.two',
            relocation_completes_at: '2026-01-01T00:00:01Z',
          }),
        )
      }),
    )
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    const stopClock = startActionClock()
    render(<PendingRelocationBanner />, { wrapper })
    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })
    expect(screen.getByText(/Relocating to Two/)).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(1_000)
    })
    act(() => {
      vi.advanceTimersByTime(1_000)
    })
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ['characters', 'me'],
      exact: true,
    })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['estates', 'me'] })
    expect(invalidate).toHaveBeenCalledTimes(6)
    stopClock()
  })

  it('clamps a contribution to held quantity and remaining target', async () => {
    const fetchMock = vi.fn(
      (input: string | URL | Request, init?: RequestInit) => {
        const path = new URL(String(input), 'http://test').pathname
        if (path === '/content/manifest')
          return Promise.resolve(
            response({ version: 'contribution-test', packs: {} }),
          )
        if (path.startsWith('/content/'))
          return Promise.resolve(
            response(contentBodies[path.slice('/content/'.length)]),
          )
        if (path === '/characters/me/inventory')
          return Promise.resolve(
            response({ items: [{ item_id: 'item.wood', quantity: 8 }] }),
          )
        if (path.includes('/contribute'))
          return Promise.resolve(
            response({ accepted_quantity: 3, body: init?.body }),
          )
        return Promise.resolve(response({}))
      },
    )
    vi.stubGlobal('fetch', fetchMock)
    render(
      <ContributionForm
        realmId="realm.one"
        projectId="project.one"
        targets={[{ item_id: 'item.wood', qty: 10 }]}
        totals={{ 'item.wood': 7 }}
      />,
      { wrapper },
    )
    const quantity = await screen.findByLabelText('Quantity')
    fireEvent.change(quantity, { target: { value: '99' } })
    expect(quantity).toHaveValue(3)
    fireEvent.click(screen.getByRole('button', { name: 'Contribute' }))
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/contribute'),
        expect.objectContaining({
          body: JSON.stringify({ item_id: 'item.wood', quantity: 3 }),
        }),
      ),
    )
  })

  it('previews then confirms relocation through the mocked endpoints', async () => {
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const url = new URL(String(input), 'http://test')
      if (url.pathname === '/content/manifest')
        return Promise.resolve(
          response({ version: 'relocate-test', packs: {} }),
        )
      if (url.pathname.startsWith('/content/'))
        return Promise.resolve(
          response(contentBodies[url.pathname.slice('/content/'.length)]),
        )
      if (url.pathname.endsWith('/preview'))
        return Promise.resolve(
          response({
            realm_id: 'realm.one',
            destination_realm_id: 'realm.two',
            cost: { gold: 25, items: [], time_ms: 60000 },
          }),
        )
      return Promise.resolve(
        response({
          realm_id: 'realm.one',
          relocating_to_realm_id: 'realm.two',
          relocation_completes_at: '2026-01-01T00:01:00Z',
          cost: { gold: 25, items: [], time_ms: 60000 },
          final_rewards: {
            cycles_completed: 0,
            xp_gained: {},
            items_consumed: {},
            items_gained: {},
            overflowed_items: {},
            level_ups: {},
            stop_reason: null,
          },
        }),
      )
    })
    vi.stubGlobal('fetch', fetchMock)
    render(
      <RelocationFlow
        currentRealmId="realm.one"
        initialDestination="realm.two"
      />,
      { wrapper },
    )
    expect(await screen.findByText('Cost: 25 gold')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm relocation' }))
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/characters/me/relocate'),
        expect.objectContaining({ method: 'POST' }),
      ),
    )
  })
})
