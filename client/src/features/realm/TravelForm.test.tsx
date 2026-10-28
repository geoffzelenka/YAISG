import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type { CharacterProfile } from '../../api/characters'
import { TravelForm } from './TravelForm'

vi.mock('../../api/content', () => ({
  useContent: () => ({ status: 'loading' }),
}))
const estate = { form: { mobility: 'mobile' }, realm_id: 'a' }
vi.mock('../../api/estates', () => ({ useEstate: () => ({ data: estate }) }))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  estate.form.mobility = 'mobile'
  estate.realm_id = 'a'
})
const profile = { character: { current_realm_id: 'a' } } as CharacterProfile
const nodes = [{ realm_id: 'b', name: 'Destination' }] as Parameters<
  typeof TravelForm
>[0]['nodes']

it('previews server edge times and supplies then starts the selected journey', async () => {
  const fetch = vi.fn((url: string, init?: RequestInit) =>
    Promise.resolve(
      new Response(
        JSON.stringify(
          init?.method === 'POST'
            ? { active: null }
            : {
                route: [
                  {
                    edge_id: 'road',
                    destination_realm_id: 'b',
                    time_ms: 4321,
                    supplies: [
                      { selector: { class: 'food', tier: 2 }, quantity: 7 },
                    ],
                  },
                ],
              },
        ),
      ),
    ),
  )
  vi.stubGlobal('fetch', fetch)
  render(
    <QueryClientProvider client={new QueryClient()}>
      <TravelForm profile={profile} nodes={nodes} />
    </QueryClientProvider>,
  )
  fireEvent.change(screen.getByLabelText('Destination'), {
    target: { value: 'b' },
  })
  fireEvent.change(screen.getByLabelText('Mode'), {
    target: { value: 'relocate' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Preview journey' }))
  expect(
    await screen.findByText(/4.32s · Supplies: 7× food/),
  ).toBeInTheDocument()
  expect(String(fetch.mock.calls[0][0])).toContain(
    'destination_realm_id=b&mode=relocate',
  )
  fireEvent.click(screen.getByRole('button', { name: 'Start journey' }))
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
  expect(fetch.mock.calls[1][1]?.body).toBe(
    JSON.stringify({ destination_realm_id: 'b', mode: 'relocate' }),
  )
})
it.each(['fixed', 'away'])(
  'disables relocate for an estate that is %s',
  (state) => {
    if (state === 'fixed') estate.form.mobility = 'fixed'
    else estate.realm_id = 'elsewhere'
    render(
      <QueryClientProvider client={new QueryClient()}>
        <TravelForm profile={profile} nodes={nodes} />
      </QueryClientProvider>,
    )
    expect(screen.getByRole('option', { name: 'Relocate' })).toBeDisabled()
  },
)

it('can default island travel to relocating the camp', async () => {
  const fetcher = vi.fn<(url: string) => Promise<Response>>(() =>
    Promise.resolve(Response.json({ route: [] })),
  )
  vi.stubGlobal('fetch', fetcher)
  render(
    <QueryClientProvider client={new QueryClient()}>
      <TravelForm
        profile={profile}
        nodes={nodes}
        initialDestination="b"
        initialMode="relocate"
      />
    </QueryClientProvider>,
  )
  expect(screen.getByLabelText('Mode')).toHaveValue('relocate')
  fireEvent.click(screen.getByText('Preview journey'))
  await waitFor(() => expect(fetcher).toHaveBeenCalled())
  expect(String(fetcher.mock.calls[0][0])).toContain('mode=relocate')
})
