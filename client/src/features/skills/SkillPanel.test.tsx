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
                    level_required: 1,
                    cycle_ms: 1000,
                    inputs: [{ item_id: 'item.input', qty: 2 }],
                    xp: 1,
                    drops: [
                      {
                        item_id: 'item.output',
                        qty: [1, 3],
                        chance: 0.5,
                      },
                    ],
                    realm_tags: ['*'],
                  },
                  {
                    id: 'a.locked',
                    name: 'Locked Node',
                    skill_id: 'gathering',
                    level_required: 5,
                    cycle_ms: 1000,
                    inputs: [],
                    xp: 1,
                    drops: [],
                    realm_tags: ['*'],
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
            market_listings: 5,
            estate_upgrade_slots: 2,
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
                    level_required: 1,
                    cycle_ms: 1000,
                    startable: true,
                    blocked_by: [],
                  },
                  {
                    action_id: 'a.locked',
                    name: 'Locked Node',
                    level_required: 5,
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
