import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, expect, it, vi } from 'vitest'

import { ContentProvider } from '../../api/content'
import { InventoryPanel } from './InventoryPanel'

function wrapper({ children }: PropsWithChildren) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <ContentProvider>{children}</ContentProvider>
    </QueryClientProvider>
  )
}

it('displays the effective profile inventory cap instead of the content base', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn((input: string | URL | Request) => {
      const path = new URL(String(input), 'http://test').pathname
      const emptyPacks: Record<string, unknown> = {
        skills: { skills: [] },
        items: { items: [] },
        realms: { realms: [] },
        upgrades: { upgrades: [] },
        caps: {
          offline_hours: 12,
          inventory_slots: 30,
          order_slots: 5,
          key_listings: 2,
          belt_slots: 2,
        },
        map: { edges: [], positions: {} },
        combatants: { combatants: [] },
        estate_forms: { forms: [] },
        development: { nodes: [] },
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
      const body =
        path === '/content/manifest'
          ? { version: 'caps-test', packs: {} }
          : path.startsWith('/content/')
            ? emptyPacks[path.slice('/content/'.length)]
            : path === '/characters/me/inventory'
              ? { items: [] }
              : {
                  character: {
                    id: 'c',
                    name: 'Hero',
                    current_realm_id: 'realm.one',
                    created_at: '',
                  },
                  skills: [],
                  gold: 0,
                  realm: {
                    id: 'realm.one',
                    name: 'One',
                    tags: [],
                    active_modifiers: [],
                  },
                  estate: {
                    id: 'e',
                    tier: 1,
                    upgrade_slots: 2,
                    installed_upgrades: [],
                  },
                  caps: {
                    offline_hours: { base: 12, effective: 14 },
                    inventory_slots: { base: 30, effective: 42 },
                    order_slots: { base: 5, effective: 5 },
                    key_listings: { base: 2, effective: 2 },
                    belt_slots: { base: 2, effective: 2 },
                    estate_upgrade_slots: { base: 2, effective: 2 },
                  },
                }
      return Promise.resolve(
        new Response(JSON.stringify(body), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    }),
  )
  render(<InventoryPanel />, { wrapper })
  expect(await screen.findByText('0 / 42 stacks')).toBeInTheDocument()
  expect(screen.queryByText('0 / 30 stacks')).not.toBeInTheDocument()
  vi.unstubAllGlobals()
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})
