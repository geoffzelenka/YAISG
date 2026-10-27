import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ContentProvider } from '../../api/content'
import { EstatePanel } from './EstatePanel'

const packs: Record<string, unknown> = {
  skills: { skills: [] },
  items: {
    items: [{ id: 'item.wood', name: 'Wood', stack_limit: 99, tags: [] }],
  },
  realms: { realms: [] },
  upgrades: {
    upgrades: [
      {
        id: 'upgrade.one',
        name: 'Wooden Roof',
        cost: [{ item_id: 'item.wood', qty: 3 }],
        modifiers: [],
        cap_bonuses: [],
        requires_realm_tags: [],
        tags: [],
      },
      {
        id: 'upgrade.two',
        name: 'Golden Roof',
        cost: [{ item_id: 'item.wood', qty: 20 }],
        modifiers: [],
        cap_bonuses: [],
        requires_realm_tags: [],
        tags: [],
      },
    ],
  },
  caps: {
    offline_hours: 12,
    inventory_slots: 30,
    order_slots: 5,
    key_listings: 2,
    belt_slots: 2,
    estate_upgrade_slots: 2,
  },
  map: { edges: [], positions: {} },
  estate_forms: { forms: [], transformations: [] },
  development: { nodes: [] },
  projects: { projects: [] },
  tags: { tags: [] },
  economy: {
    decay: { faltering_factor: 0.5 },
    transition: { duration_days: 7 },
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

function wrapper({ children }: PropsWithChildren) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <ContentProvider>{children}</ContentProvider>
    </QueryClientProvider>
  )
}

describe('estate panel', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('renders active, inert, and empty slots and gates upgrade affordability', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: string | URL | Request) => {
        const path = new URL(String(input), 'http://test').pathname
        const body =
          path === '/content/manifest'
            ? { version: 'estate-test', packs: {} }
            : path.startsWith('/content/')
              ? packs[path.slice('/content/'.length)]
              : path === '/characters/me/inventory'
                ? { items: [{ item_id: 'item.wood', quantity: 5 }] }
                : {
                    id: 'estate',
                    form: {
                      id: 'form.camp',
                      name: 'Camp',
                      specialty_tags: ['mobile'],
                      mobility: 'mobile',
                      travel_profile: {
                        time_mult: 1,
                        supply_mult: 1,
                        terrains: ['land'],
                      },
                      base_caps: { estate_upgrade_slots: 3 },
                      modifiers: [],
                    },
                    realm_id: 'realm.one',
                    level: 2,
                    status: 'active',
                    upgrade_slots: 3,
                    installed_upgrades: [
                      {
                        slot_index: 0,
                        upgrade_id: 'installed.active',
                        name: 'Active Tent',
                        status: 'active',
                        inert_reason: null,
                      },
                      {
                        slot_index: 1,
                        upgrade_id: 'installed.inert',
                        name: 'Dormant Bell',
                        status: 'inert',
                        inert_reason: 'realm requirements not met',
                      },
                    ],
                  }
        return Promise.resolve(
          new Response(JSON.stringify(body), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        )
      }),
    )
    render(<EstatePanel />, { wrapper })

    expect(await screen.findByText('Active Tent')).toBeInTheDocument()
    expect(screen.getByText('Dormant Bell')).toBeInTheDocument()
    expect(screen.getByText('inert')).toHaveAttribute(
      'title',
      'realm requirements not met',
    )
    expect(screen.getByTestId('estate-slot-2')).toHaveTextContent('Empty')
    expect(screen.getByRole('button', { name: 'Purchase' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Cannot afford' })).toBeDisabled()
  })
})
