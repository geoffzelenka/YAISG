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
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import type { CharacterProfile } from '../../api/characters'
import { RealmMarketPanel } from './RealmMarketPanel'
import { MapPanel } from '../realm/MapPanel'

vi.mock('../realm/TravelForm', () => ({ TravelForm: () => null }))
vi.mock('../../api/http', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../api/http')>()),
  gameRequest: (path: string, init?: RequestInit) => fetch(path, init),
}))
const market = {
  lines: [
    {
      line_key: 'food',
      selector: { class: 'food' },
      stock: 1000,
      reserve: 4000,
      cap: 8000,
      days_of_cover: 0.5,
      members: [
        {
          item_id: 'sprig',
          spot_bid: '2.12345678',
          funded_quantity: 2,
          funded_total: 4,
        },
      ],
    },
  ],
  for_sale: [{ item_id: 'sprig', quantity: 3, spot_ask: 5 }],
  shortfalls: [{ line_key: 'food', missing_milli: 1000 }],
  decay_stage: 'strained',
  gauge_days: 2,
  treasury_band: '1',
}
let moved = false
let quoteGold = 4
const requests: { path: string; body: unknown }[] = []
function setup(
  present = true,
  component: 'market' | 'map' = 'market',
  options: { equalGauge?: boolean; healthy?: boolean } = {},
) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, init?: RequestInit) => {
      await Promise.resolve()
      requests.push({
        path,
        body: init?.body ? JSON.parse(String(init.body)) : null,
      })
      if (path === '/map')
        return Response.json({
          nodes: [
            {
              realm_id: options.equalGauge ? 'Zrealm' : 'home',
              name: 'Home',
              gauge: 2,
              decay_stage: 'strained',
              treasury_band: '1',
              position: null,
            },
            {
              realm_id: options.equalGauge ? 'arealm' : 'away',
              name: 'Away',
              gauge: options.equalGauge ? 2 : 5,
              decay_stage: 'faltering',
              treasury_band: '0',
              position: null,
            },
          ],
          edges: [],
        })
      if (path.endsWith('/treasury/gift'))
        return new Response(null, { status: 204 })
      if (path.endsWith('/trade') && moved) {
        moved = false
        quoteGold = 6
        return Response.json(
          { error: { code: 'PRICE_MOVED', message: 'Changed' } },
          { status: 409 },
        )
      }
      if (path.endsWith('/trade'))
        return Response.json({ gold: quoteGold, max_quantity: 1 })
      if (path.includes('/quote?'))
        return Response.json({ gold: quoteGold, max_quantity: 2 })
      return Response.json(
        options.healthy
          ? {
              ...market,
              lines: market.lines.map((line) => ({
                ...line,
                stock: line.reserve,
              })),
            }
          : market,
      )
    }),
  )
  const profile = {
    character: { current_realm_id: present ? 'home' : 'away' },
  } as CharacterProfile
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter initialEntries={['/realm/market?realm=home']}>
        {component === 'map' ? (
          <MapPanel profile={profile} />
        ) : (
          <RealmMarketPanel profile={profile} />
        )}
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  requests.length = 0
  moved = false
  quoteGold = 4
})
async function getQuote() {
  await screen.findByText('Demand lines')
  fireEvent.change(screen.getByLabelText('Item'), {
    target: { value: 'sprig' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Get quote' }))
  return screen.findByRole('button', { name: 'Confirm trade' })
}
it('quotes then confirms with the exact integrated limit_gold', async () => {
  setup()
  fireEvent.click(await getQuote())
  await waitFor(() =>
    expect(requests.find((r) => r.path.endsWith('/trade'))?.body).toEqual({
      item_id: 'sprig',
      side: 'sell',
      quantity: 1,
      limit_gold: 4,
    }),
  )
})
it('PRICE_MOVED re-quotes and requires another confirmation', async () => {
  setup()
  moved = true
  fireEvent.click(await getQuote())
  expect(await screen.findByText(/Review the new quote/)).toBeInTheDocument()
  await screen.findByText(/Receive 6 gold/)
  expect(
    requests.filter((r) => r.path === '/realms/home/market').length,
  ).toBeGreaterThan(1)
  expect(requests.filter((r) => r.path.endsWith('/trade'))).toHaveLength(1)
  fireEvent.click(screen.getByRole('button', { name: 'Confirm trade' }))
  await waitFor(() =>
    expect(
      requests.filter((r) => r.path.endsWith('/trade'))[1]?.body,
    ).toMatchObject({ limit_gold: 6 }),
  )
})
it('trade and gift are disabled when not present while market stays readable', async () => {
  setup(false)
  expect(await getQuote()).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Give gold' })).toBeDisabled()
  expect(requests.some((r) => r.path.endsWith('/trade'))).toBe(false)
})
it('shortfalls render without a buy button and member alternatives retain units', async () => {
  setup()
  await screen.findByText(/missing 1 line units/)
  expect(
    within(screen.getByRole('list', { name: 'Shortfalls' })).queryByRole(
      'button',
    ),
  ).not.toBeInTheDocument()
  expect(screen.getByText(/Funded quantity: 2/)).toHaveTextContent('2.12345678')
  expect(screen.getByText(/Stock: 1/)).toHaveTextContent('Cover: 0.50 days')
  expect(screen.getByText(/Gauge:/)).toHaveTextContent('Gauge: 2.00 days')
})
it('gifts require confirmation and accept a 204 response', async () => {
  setup()
  await screen.findByText('Demand lines')
  fireEvent.click(screen.getByRole('button', { name: 'Give gold' }))
  expect(requests.some((r) => r.path.endsWith('/treasury/gift'))).toBe(false)
  fireEvent.click(
    within(screen.getByRole('dialog')).getByRole('button', {
      name: 'Confirm gift',
    }),
  )
  await waitFor(() =>
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument(),
  )
  expect(screen.getByRole('status')).toHaveTextContent(
    'Gave 1 gold to this realm.',
  )
  expect(requests.find((r) => r.path.endsWith('/treasury/gift'))?.body).toEqual(
    { gold: 1 },
  )
})
it('hungry realms sort by descending gauge and display short lines, stage and band', async () => {
  setup(true, 'map')
  await screen.findAllByText(/short 3 line units/)
  expect(screen.getAllByRole('link').map((link) => link.textContent)).toEqual([
    'Away',
    'Home',
  ])
  expect(screen.getByText(/Tier.*strained/)).toHaveTextContent(
    'strained · Gauge: 2.00 days · Treasury: 1',
  )
})

it('editing trade intent discards the quote; buying confirms the quoted maximum spend', async () => {
  setup()
  await getQuote()
  fireEvent.change(screen.getByLabelText('Quantity'), {
    target: { value: '2' },
  })
  expect(
    screen.queryByRole('button', { name: 'Confirm trade' }),
  ).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Side'), { target: { value: 'buy' } })
  fireEvent.change(screen.getByLabelText('Item'), {
    target: { value: 'sprig' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Get quote' }))
  expect(await screen.findByText(/Pay 4 gold/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Confirm trade' }))
  await waitFor(() =>
    expect(requests.find((r) => r.path.endsWith('/trade'))?.body).toEqual({
      item_id: 'sprig',
      side: 'buy',
      quantity: 2,
      limit_gold: 4,
    }),
  )
})

it.each([400, 409])(
  'displays NO_DEMAND regardless of HTTP status %s',
  async (status) => {
    setup()
    const fetchMock = vi.mocked(fetch)
    await screen.findByText('Demand lines')
    fetchMock.mockResolvedValueOnce(
      Response.json(
        {
          error: {
            code: 'NO_DEMAND',
            message: 'The realm has no demand for this item',
          },
        },
        { status },
      ),
    )
    fireEvent.change(screen.getByLabelText('Item'), {
      target: { value: 'sprig' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Get quote' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The realm has no demand for this item (NO_DEMAND)',
    )
    expect(
      screen.queryByRole('button', { name: 'Confirm trade' }),
    ).not.toBeInTheDocument()
  },
)

it('reports the largest fundable quantity on UNFUNDED_DEMAND', async () => {
  setup()
  const confirm = await getQuote()
  vi.mocked(fetch).mockResolvedValueOnce(
    Response.json(
      {
        error: {
          code: 'UNFUNDED_DEMAND',
          message: 'Demand is unfunded',
          max_quantity: 0,
        },
      },
      { status: 409 },
    ),
  )
  fireEvent.click(confirm)
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Maximum fundable: 0 items',
  )
  expect(
    screen.queryByRole('button', { name: 'Confirm trade' }),
  ).not.toBeInTheDocument()
})

it.each(['trade', 'gift'] as const)(
  'double-clicking confirm sends exactly one %s request',
  async (kind) => {
    setup()
    let confirm: HTMLElement
    if (kind === 'trade') confirm = await getQuote()
    else {
      await screen.findByText('Demand lines')
      fireEvent.click(screen.getByRole('button', { name: 'Give gold' }))
      confirm = screen.getByRole('button', { name: 'Confirm gift' })
    }
    const fetchMock = vi.mocked(fetch)
    const original = fetchMock.getMockImplementation()!
    let finish!: (response: Response) => void
    const pending = new Promise<Response>((resolve) => {
      finish = resolve
    })
    const suffix = kind === 'trade' ? '/trade' : '/treasury/gift'
    fetchMock.mockImplementation((path, init) =>
      String(path).endsWith(suffix) ? pending : original(path, init),
    )
    act(() => {
      fireEvent.click(confirm)
      fireEvent.click(confirm)
    })
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.filter(([path]) => String(path).endsWith(suffix)),
      ).toHaveLength(1),
    )
    finish(
      kind === 'trade'
        ? Response.json({ gold: 3, max_quantity: 1 })
        : new Response(null, { status: 204 }),
    )
    expect(
      await screen.findByText(
        kind === 'trade'
          ? 'Sold 1 sprig for 3 gold.'
          : 'Gave 1 gold to this realm.',
      ),
    ).toBeInTheDocument()
  },
)

it('trade success reports the actual execution response instead of the quote', async () => {
  setup()
  const confirm = await getQuote()
  vi.mocked(fetch).mockResolvedValueOnce(
    Response.json({ gold: 3, max_quantity: 1 }),
  )
  fireEvent.click(confirm)
  expect(await screen.findByText('Sold 1 sprig for 3 gold.')).toHaveAttribute(
    'role',
    'status',
  )
})

it('gift success clears an earlier error before sending', async () => {
  setup()
  const confirm = await getQuote()
  vi.mocked(fetch).mockResolvedValueOnce(
    Response.json(
      { error: { code: 'NOT_PRESENT', message: 'Absent' } },
      { status: 409 },
    ),
  )
  fireEvent.click(confirm)
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Absent (NOT_PRESENT)',
  )
  fireEvent.click(screen.getByRole('button', { name: 'Give gold' }))
  let finish!: (response: Response) => void
  vi.mocked(fetch).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve
      }),
  )
  fireEvent.click(screen.getByRole('button', { name: 'Confirm gift' }))
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  await waitFor(() => expect(finish).toBeDefined())
  finish(new Response(null, { status: 204 }))
  expect(await screen.findByRole('status')).toHaveTextContent(
    'Gave 1 gold to this realm.',
  )
})

it('equal gauges sort realm ids by code point', async () => {
  setup(true, 'map', { equalGauge: true })
  await screen.findAllByText(/short 3 line units/)
  expect(screen.getAllByRole('link').map((link) => link.textContent)).toEqual([
    'Home',
    'Away',
  ])
  expect(screen.getAllByText(/Gauge: 2.00 days/)).toHaveLength(4)
})

it('shows an empty hungry list only after every market has loaded without short lines', async () => {
  setup(true, 'map', { healthy: true })
  const fetchMock = vi.mocked(fetch)
  const original = fetchMock.getMockImplementation()!
  let finish!: (response: Response) => void
  const pending = new Promise<Response>((resolve) => {
    finish = resolve
  })
  fetchMock.mockImplementation((path, init) =>
    String(path) === '/realms/away/market' ? pending : original(path, init),
  )
  await screen.findByText(/Loading short lines/)
  await waitFor(() =>
    expect(
      screen.queryByRole('link', { name: 'Home' }),
    ).not.toBeInTheDocument(),
  )
  expect(
    screen.queryByText('No realm is below reserve.'),
  ).not.toBeInTheDocument()
  finish(Response.json({ ...market, lines: [] }))
  expect(
    await screen.findByText('No realm is below reserve.'),
  ).toBeInTheDocument()
  expect(screen.queryByRole('link')).not.toBeInTheDocument()
})
