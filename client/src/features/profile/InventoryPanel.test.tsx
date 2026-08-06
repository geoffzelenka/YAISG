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
          market_listings: 5,
          estate_upgrade_slots: 2,
        },
        map: { edges: [], positions: {} },
        estate_forms: { forms: [], transformations: [] },
        development: { nodes: [], edges: [] },
        projects: { projects: [] },
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
                    realm_id: 'realm.one',
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
                    level: 1,
                    upgrade_slots: 2,
                    installed_upgrades: [],
                  },
                  caps: {
                    offline_hours: { base: 12, effective: 14 },
                    inventory_slots: { base: 30, effective: 42 },
                    market_listings: { base: 5, effective: 5 },
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
