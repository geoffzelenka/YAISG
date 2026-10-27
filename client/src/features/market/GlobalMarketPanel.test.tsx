import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type { CharacterProfile } from '../../api/characters'
import { GlobalMarketPanel } from './GlobalMarketPanel'

const marketContent = vi.hoisted(() => ({
  settings: { tax_pct: 5, order_days: 14 } as
    | { tax_pct?: number; order_days?: number }
    | undefined,
}))

vi.mock('../../api/content', () => ({
  useContent: () => ({
    status: 'ready',
    content: {
      tags: { tags: [{ id: 'access', effects: { market_access: true } }] },
      items: {
        items: [
          { id: 'twig', name: 'Twig' },
          { id: 'key', name: 'Key', instanced: true },
        ],
      },
      economy: { market: marketContent.settings },
    },
  }),
}))
vi.mock('../../api/http', async (original) => ({
  ...(await original<typeof import('../../api/http')>()),
  gameRequest: (path: string, init?: RequestInit) => fetch(path, init),
}))
const order = {
  id: 'slot',
  side: 'buy',
  item_id: 'twig',
  quantity: 5,
  quantity_remaining: 3,
  unit_price: 9,
  escrow_gold_remaining: 27,
  fill_items: 2,
  fill_gold: 4,
  status: 'open',
  expires_at: '2030-01-01',
}
const fill = {
  id: 'fill',
  side: 'buy',
  item_id: 'twig',
  quantity: 2,
  unit_price: 7,
  tax_gold: 1,
  matched_at: '2026-10-27',
}
function setup(access = true) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const invalidate = vi.spyOn(client, 'invalidateQueries')
  const mock = vi.fn(
    async (path: string, init?: RequestInit): Promise<Response> => {
      await Promise.resolve()
      if (path === '/realms/home')
        return Response.json({ active_tags: access ? ['access'] : [] })
      if (path.includes('/book/'))
        return Response.json({
          buy: [{ unit_price: 8, quantity: 12 }],
          sell: [],
        })
      if (path.includes('/history/'))
        return Response.json({
          matches: [
            { ...fill, id: path.includes('before=') ? 'older-fill' : fill.id },
          ],
          next_cursor: path.includes('before=') ? null : 'opaque+cursor',
        })
      if (path.endsWith('/collect'))
        return Response.json({
          order: { ...order, fill_items: 1, fill_gold: 0 },
          collected: { items: 1, gold: 4 },
        })
      if (path.endsWith('/cancel'))
        return Response.json({ order: { ...order, status: 'collectable' } })
      if (init?.method === 'POST')
        return Response.json({ order, fills: [fill] }, { status: 201 })
      return Response.json({
        orders: [
          order,
          { ...order, id: 'expired', status: 'collectable' },
          {
            ...order,
            id: 'closed',
            status: 'closed',
            fill_items: 0,
            fill_gold: 0,
          },
        ],
      })
    },
  )
  vi.stubGlobal('fetch', mock)
  render(
    <QueryClientProvider client={client}>
      <GlobalMarketPanel
        profile={
          {
            character: { current_realm_id: 'home' },
            caps: { order_slots: { effective: 4 } },
          } as CharacterProfile
        }
      />
    </QueryClientProvider>,
  )
  return { mock, invalidate }
}
afterEach(() => {
  cleanup()
  marketContent.settings = { tax_pct: 5, order_days: 14 }
  vi.unstubAllGlobals()
})
async function choose() {
  await screen.findByText('Market access available.')
  fireEvent.change(screen.getByLabelText('Good'), { target: { value: 'twig' } })
}
it('access-gated controls leave books, history and cancellation available', async () => {
  const { mock } = setup(false)
  await screen.findByText(/No market access in your current realm/)
  for (const button of screen.getAllByRole('button', { name: 'Collect' }))
    expect(button).toBeDisabled()
  expect(screen.queryByRole('option', { name: 'Key' })).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Good'), { target: { value: 'twig' } })
  await screen.findByText('12')
  const place = screen.getByRole('button', { name: 'Place order' })
  expect(place).toBeDisabled()
  for (const label of ['Side', 'Quantity', 'Unit price'])
    expect(screen.getByLabelText(label)).toBeDisabled()
  fireEvent.submit(place.closest('form')!)
  await act(async () => {
    await Promise.resolve()
  })
  expect(
    mock.mock.calls.filter(
      ([path, init]) => path === '/market/orders' && init?.method === 'POST',
    ),
  ).toHaveLength(0)
  fireEvent.click(
    within(screen.getByRole('article', { name: 'Order slot' })).getByText(
      'Cancel order',
    ),
  )
  await screen.findByText(/Order cancelled/)
  expect(mock.mock.calls.some(([path]) => path.endsWith('/cancel'))).toBe(true)
})
it('slot state rendering and partial collection report actual transfers and invalidate holders', async () => {
  const { invalidate } = setup()
  await choose()
  expect(await screen.findByText('Slots used: 2 / 4')).toBeInTheDocument()
  const open = within(screen.getByRole('article', { name: 'Order slot' }))
  expect(open.getByText('buy Twig · open')).toBeInTheDocument()
  expect(open.getByText(/Waiting: 2 items and 4 gold/)).toBeInTheDocument()
  expect(open.getByText('Cancel order')).toBeEnabled()
  const expired = within(screen.getByRole('article', { name: 'Order expired' }))
  expect(expired.getByText('buy Twig · collectable')).toBeInTheDocument()
  expect(expired.getByText('Cancel order')).toBeDisabled()
  const closed = within(screen.getByRole('article', { name: 'Order closed' }))
  expect(closed.getByText('Collect')).toBeDisabled()
  expect(closed.getByText('Cancel order')).toBeDisabled()
  fireEvent.click(
    within(screen.getByRole('article', { name: 'Order slot' })).getByText(
      'Collect',
    ),
  )
  expect(await screen.findByRole('status')).toHaveTextContent(
    'Collected 1 item and 4 gold. Partial collection: 1 item and 0 gold remain in the slot',
  )
  for (const key of ['characters', 'realms', 'estates', 'map', 'global-market'])
    expect(invalidate).toHaveBeenCalledWith({ queryKey: [key] })
})
it('immediate-fill report uses server execution and leaves proceeds in slots', async () => {
  const { mock } = setup()
  await choose()
  fireEvent.change(screen.getByLabelText('Quantity'), {
    target: { value: '5' },
  })
  fireEvent.change(screen.getByLabelText('Unit price'), {
    target: { value: '9' },
  })
  fireEvent.click(screen.getByText('Place order'))
  await screen.findByText('Immediate fills')
  expect(screen.getByRole('status')).toHaveTextContent(
    'Slot holds 2 items and 4 gold. Collect to move',
  )
  expect(screen.getAllByText(/buy 2 Twig at 7 gold each/)).toHaveLength(2)
  expect(
    JSON.parse(
      String(
        mock.mock.calls.find(([path]) => path === '/market/orders')?.[1]?.body,
      ),
    ),
  ).toEqual({ side: 'buy', quantity: 5, unit_price: 9, item_id: 'twig' })
})
it('history passes the opaque cursor and book depth to the server', async () => {
  const { mock } = setup()
  await choose()
  fireEvent.change(screen.getByLabelText('Book depth'), {
    target: { value: '50' },
  })
  await waitFor(() =>
    expect(
      mock.mock.calls.some(([path]) => path === '/market/book/twig?depth=50'),
    ).toBe(true),
  )
  fireEvent.click(await screen.findByText('Load older trades'))
  await waitFor(() =>
    expect(
      mock.mock.calls.some(([path]) => path.includes('before=opaque%2Bcursor')),
    ).toBe(true),
  )
  await waitFor(() =>
    expect(screen.queryByText('Load older trades')).not.toBeInTheDocument(),
  )
})
it('double submission sends one request and MARKET_RETRY is surfaced without resubmission', async () => {
  const { mock } = setup()
  await choose()
  const original = mock.getMockImplementation()!
  let finish!: (response: Response) => void
  mock.mockImplementation((path, init) =>
    path === '/market/orders'
      ? new Promise((resolve) => {
          finish = resolve
        })
      : original(path, init),
  )
  act(() => {
    fireEvent.click(screen.getByText('Place order'))
    fireEvent.click(screen.getByText('Place order'))
  })
  await waitFor(() =>
    expect(
      mock.mock.calls.filter(([path]) => path === '/market/orders'),
    ).toHaveLength(1),
  )
  finish(
    Response.json(
      { error: { code: 'MARKET_RETRY', message: 'Retry transaction' } },
      { status: 409 },
    ),
  )
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'MARKET_RETRY) Please retry',
  )
  expect(
    mock.mock.calls.filter(([path]) => path === '/market/orders'),
  ).toHaveLength(1)
})

it('sell intent and a resting order do not imply an immediate fill', async () => {
  const { mock } = setup()
  await choose()
  const original = mock.getMockImplementation()!
  mock.mockImplementation((path, init) =>
    path === '/market/orders'
      ? Promise.resolve(
          Response.json(
            {
              order: {
                ...order,
                side: 'sell',
                quantity_remaining: 5,
                fill_items: 0,
                fill_gold: 0,
              },
              fills: [],
            },
            { status: 201 },
          ),
        )
      : original(path, init),
  )
  fireEvent.change(screen.getByLabelText('Side'), { target: { value: 'sell' } })
  fireEvent.click(screen.getByText('Place order'))
  expect(await screen.findByRole('status')).toHaveTextContent(
    'Remaining on book: 5. Slot holds 0 items and 0 gold.',
  )
  expect(screen.queryByText('Immediate fills')).not.toBeInTheDocument()
  expect(
    JSON.parse(
      String(
        mock.mock.calls.find(([path]) => path === '/market/orders')?.[1]?.body,
      ),
    ),
  ).toMatchObject({ side: 'sell' })
})

it.each(['NO_MARKET_ACCESS', 'MARKET_RETRY', 'INSUFFICIENT_GOLD'])(
  '%s refreshes current realm access after mutation failure',
  async (code) => {
    const { mock, invalidate } = setup()
    await choose()
    const original = mock.getMockImplementation()!
    mock.mockImplementation((path, init) => {
      if (path === '/market/orders')
        return Promise.resolve(
          Response.json(
            { error: { code, message: 'Order rejected' } },
            { status: 409 },
          ),
        )
      if (path === '/realms/home')
        return Promise.resolve(Response.json({ active_tags: [] }))
      return original(path, init)
    })
    fireEvent.click(screen.getByText('Place order'))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      `Order rejected (${code})`,
    )
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['realms', 'home'] })
    await screen.findByText(/No market access in your current realm/)
    expect(screen.getByText('Place order')).toBeDisabled()
  },
)

it('collecting all waiting holdings from an open order reports nothing waiting right now', async () => {
  const { mock } = setup()
  await choose()
  const original = mock.getMockImplementation()!
  mock.mockImplementation((path, init) =>
    path.endsWith('/collect')
      ? Promise.resolve(
          Response.json({
            order: { ...order, fill_items: 0, fill_gold: 0 },
            collected: { items: 2, gold: 4 },
          }),
        )
      : original(path, init),
  )
  fireEvent.click(
    within(screen.getByRole('article', { name: 'Order slot' })).getByText(
      'Collect',
    ),
  )
  expect(await screen.findByRole('status')).toHaveTextContent(
    'Collected 2 items and 4 gold. Nothing is waiting right now.',
  )
})

it.each([undefined, { tax_pct: 5 }, { order_days: 14 }])(
  'omits incomplete tax and expiry settings %j',
  async (settings) => {
    marketContent.settings = settings
    setup()
    await choose()
    expect(screen.queryByText(/Seller tax: 5%/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Orders expire after/)).not.toBeInTheDocument()
  },
)
