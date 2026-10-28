import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { KeysPanel } from './KeysPanel'

vi.mock('../../api/content', () => ({
  useContent: () => ({ status: 'loading' }),
}))
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})
it('starts keys by instance, lists at a fixed price, retains filters on cursor pages, and pins buy price', async () => {
  const key = {
    id: 'held',
    template_id: 'template',
    discovered_by_name: 'Finder',
    realm_id: 'home',
    payload: { action: { name: 'Resource', outputs: [] } },
    state: 'active',
    uses_total: 5,
    uses_remaining: 5,
    bound_at: null,
  }
  const calls: { path: string; body: unknown }[] = []
  const fetcher = vi
    .spyOn(globalThis, 'fetch')
    .mockImplementation((url, init) => {
      const path = new URL(String(url)).pathname
      if (init?.method === 'POST') {
        calls.push({
          path,
          body: init.body
            ? (JSON.parse(String(init.body)) as unknown)
            : undefined,
        })
        return Promise.resolve(Response.json({}))
      }
      return Promise.resolve(
        Response.json(
          path === '/keys/me'
            ? { keys: [key] }
            : {
                listings: [
                  { id: 'listing', key, price_gold: 12, deprecated: true },
                ],
                next_cursor: new URL(String(url)).searchParams.has('before')
                  ? null
                  : 'opaque',
              },
        ),
      )
    })
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <KeysPanel />
    </QueryClientProvider>,
  )
  fireEvent.click(await screen.findByText('Start Resource'))
  await waitFor(() =>
    expect(calls[0]).toEqual({
      path: '/actions/start',
      body: { key_id: 'held' },
    }),
  )
  await waitFor(() => expect(screen.getByText('List key')).toBeEnabled())
  fireEvent.change(screen.getByLabelText('Unused key'), {
    target: { value: 'held' },
  })
  fireEvent.change(screen.getByLabelText('Price in gold'), {
    target: { value: '9' },
  })
  fireEvent.submit(screen.getByText('List key').closest('form')!)
  await waitFor(() =>
    expect(calls[1]).toEqual({
      path: '/keys/market',
      body: { instance_id: 'held', price_gold: 9 },
    }),
  )
  fireEvent.change(screen.getByLabelText('goods class'), {
    target: { value: 'ore' },
  })
  await waitFor(() => expect(screen.getByText('Next page')).toBeEnabled())
  fireEvent.click(screen.getByText('Next page'))
  await waitFor(() =>
    expect(
      fetcher.mock.calls.some(
        ([url]) =>
          String(url).includes('class=ore') &&
          String(url).includes('before=opaque'),
      ),
    ).toBe(true),
  )
  await waitFor(() => expect(screen.getByText('Buy key')).toBeEnabled())
  fireEvent.click(screen.getByText('Buy key'))
  await waitFor(() =>
    expect(calls[2]).toEqual({
      path: '/keys/market/listing/buy',
      body: { price_gold: 12 },
    }),
  )
})
