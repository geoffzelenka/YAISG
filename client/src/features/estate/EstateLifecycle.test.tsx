import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type { Content } from '../../api/content'
import type { Estate } from '../../api/estates'
import { EstateLifecycle } from './EstateLifecycle'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})
it('build confirmation lists the mobile estate upgrades before any payment', async () => {
  const fetch = vi.fn((input: string) =>
    Promise.resolve(
      new Response(
        JSON.stringify(
          input.endsWith('/characters/me')
            ? { character: { current_realm_id: 'home' } }
            : input.endsWith('/inventory')
              ? { items: [] }
              : [{ id: 'sale', form: 'house', sale_price: 25 }],
        ),
      ),
    ),
  )
  vi.stubGlobal('fetch', fetch)
  const client = new QueryClient()
  const estate = {
    realm_id: 'home',
    gauge: 0,
    surrender_value: null,
    form: { id: 'tent', name: 'Mobile Tent', mobility: 'mobile' },
    installed_upgrades: [{ name: 'Roof' }, { name: 'Bell' }],
    larder: { wood: 7500 },
  } as unknown as Estate
  const content = {
    estate_forms: {
      forms: [
        {
          id: 'tent',
          name: 'Mobile Tent',
          transforms_to: [],
          upkeep: [{ selector: { item: 'wood' }, per_day: 3 }],
        },
        {
          id: 'house',
          name: 'House',
          mobility: 'fixed',
          tier: 1,
          transforms_to: [],
          requires_realm_tags: [],
          build_cost: {
            gold: 12,
            goods: [{ selector: { item: 'wood' }, quantity: 2 }],
          },
        },
      ],
    },
    items: { items: [{ id: 'wood', name: 'Wood' }] },
  } as unknown as Content
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <EstateLifecycle estate={estate} content={content} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  await screen.findByText(/Present at estate/)
  expect(screen.getByText('wood: 2.50 days of cover')).toBeInTheDocument()
  fireEvent.click(
    await screen.findByRole('button', { name: 'Buy House · 25 gold' }),
  )
  expect(screen.getByRole('dialog')).toHaveTextContent(
    'Buy House for current price 25 gold',
  )
  expect(screen.getByRole('dialog')).not.toHaveTextContent('Buy house')
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
  fireEvent.click(screen.getByRole('button', { name: 'Build House' }))
  const dialog = screen.getByRole('dialog')
  expect(dialog).toHaveTextContent('12 gold')
  expect(dialog).toHaveTextContent('2 wood')
  expect(dialog).toHaveTextContent('Mobile Tent, its larder')
  expect(dialog).toHaveTextContent('Roof, Bell')
  expect(fetch.mock.calls.every(([url]) => !url.endsWith('/build'))).toBe(true)
  fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})
