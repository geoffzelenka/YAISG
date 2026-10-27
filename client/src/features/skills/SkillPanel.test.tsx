import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ContentProvider } from '../../api/content'
import { SkillPanel } from './SkillPanel'

function wrapper({ children }: PropsWithChildren) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <ContentProvider>{children}</ContentProvider>
    </QueryClientProvider>
  )
}

describe('skill panel', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders startable and locked actions from server fixtures', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: string | URL | Request) => {
        const path = new URL(String(input), 'http://test').pathname
        const bodies: Record<string, unknown> = {
          '/content/manifest': { version: 'test', packs: {} },
          '/content/skills': {
            skills: [
              {
                id: 'gathering',
                name: 'Gathering',
                actions: [
                  {
                    id: 'a.open',
                    name: 'Open Node',
                    skill_id: 'gathering',
                    unlock_level: 1,
                    base_cycle_ms: 1000,
                    inputs: [{ selector: { item: 'item.input' }, quantity: 2 }],
                    xp: 1,
                    outputs: [
                      {
                        item_id: 'item.output',
                        quantity_min: 1,
                        quantity_max: 3,
                        chance: 0.5,
                      },
                    ],
                    requires: { realm_tags: ['*'] },
                  },
                  {
                    id: 'a.locked',
                    name: 'Locked Node',
                    skill_id: 'gathering',
                    unlock_level: 5,
                    base_cycle_ms: 1000,
                    inputs: [],
                    xp: 1,
                    outputs: [],
                    requires: { realm_tags: ['*'] },
                  },
                ],
              },
            ],
          },
          '/content/items': {
            items: [
              {
                id: 'item.input',
                name: 'Input Item',
                stack_limit: 99,
                tags: [],
              },
              {
                id: 'item.output',
                name: 'Output Item',
                stack_limit: 99,
                tags: [],
              },
            ],
          },
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
          '/content/map': { edges: [], positions: {} },
          '/content/estate_forms': {
            forms: [],
            transformations: [],
            relocation_classes: {},
          },
          '/content/development': { nodes: [], edges: [] },
          '/content/projects': { projects: [] },
          '/content/progression': {
            tier_thresholds: [1],
            tier_titles: ['Placeholder'],
          },
          '/characters/me/actions/available': {
            skills: [
              {
                skill_id: 'gathering',
                name: 'Gathering',
                actions: [
                  {
                    action_id: 'a.open',
                    name: 'Open Node',
                    unlock_level: 1,
                    cycle_ms: 1000,
                    startable: true,
                    blocked_by: [],
                  },
                  {
                    action_id: 'a.locked',
                    name: 'Locked Node',
                    unlock_level: 5,
                    cycle_ms: 1000,
                    startable: false,
                    blocked_by: ['INSUFFICIENT_LEVEL'],
                  },
                ],
              },
            ],
          },
        }
        return Promise.resolve(
          new Response(JSON.stringify(bodies[path]), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        )
      }),
    )
    render(<SkillPanel skillId="gathering" />, { wrapper })
    expect(
      await screen.findByRole('heading', { name: 'Open Node' }),
    ).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Start' })[0]).toBeEnabled()
    expect(screen.getByText('Locked: insufficient level')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Start' })[1]).toBeDisabled()
    expect(screen.getByText('2× Input Item')).toBeInTheDocument()
    expect(screen.getByText('1–3× Output Item (50%)')).toBeInTheDocument()
  })
})
