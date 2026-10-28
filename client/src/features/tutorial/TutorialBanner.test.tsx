import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { expect, it, vi } from 'vitest'
import type { CharacterProfile } from '../../api/characters'
import { TutorialBanner } from './TutorialBanner'

vi.mock('../realm/TravelForm', () => ({ TravelForm: () => null }))
vi.mock('../../api/content', () => ({
  useContent: () => ({
    status: 'ready',
    content: {
      tutorial: {
        realm_1: 'one',
        realm_2: 'two',
        arrival_realms: ['world'],
        steps: [
          { id: 'first', hint: 'Gather supplies' },
          { id: 'last', hint: 'Set sail' },
        ],
      },
      realms: { realms: [{ id: 'world', name: 'The world' }] },
    },
  }),
}))
function profile(step: string | null) {
  return {
    character: { tutorial_step: step, current_realm_id: 'two:owner' },
  } as CharacterProfile
}
it('updates the hint from the current server step and hides it after departure', () => {
  const client = new QueryClient()
  const view = (step: string | null) => (
    <QueryClientProvider client={client}>
      <TutorialBanner profile={profile(step)} />
    </QueryClientProvider>
  )
  const { rerender } = render(view('first'))
  expect(screen.getByRole('status')).toHaveTextContent('Gather supplies')
  rerender(view('last'))
  expect(screen.getByRole('status')).toHaveTextContent('Set sail')
  rerender(view(null))
  expect(screen.queryByLabelText('Tutorial')).not.toBeInTheDocument()
})
it('blocks guest departure, upgrades in place, confirms game promotion, then departs', async () => {
  let full = false
  const calls: string[] = []
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, init) => {
    await Promise.resolve()
    const path = String(url)
    calls.push(path)
    if (path.endsWith('/auth/upgrade'))
      return new Response(JSON.stringify({ access_token: 'full-token' }))
    if (path.endsWith('/players/me')) {
      expect(new Headers(init?.headers).get('Authorization')).toBe(
        'Bearer full-token',
      )
      full = true
      return new Response('{}')
    }
    expect(JSON.parse(String(init?.body))).toEqual({
      destination_realm_id: 'world',
    })
    return full
      ? new Response('{}')
      : new Response(
          JSON.stringify({
            error: { code: 'ACCOUNT_REQUIRED', message: 'Register first' },
          }),
          { status: 403 },
        )
  })
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { mutations: { retry: false } } })
      }
    >
      <TutorialBanner profile={profile('last')} />
    </QueryClientProvider>,
  )
  fireEvent.change(screen.getByLabelText('World destination'), {
    target: { value: 'world' },
  })
  fireEvent.submit(screen.getByText('Depart Tutorial Island').closest('form')!)
  await screen.findByText('Upgrade account')
  expect(screen.getByText('Depart Tutorial Island')).toBeDisabled()
  fireEvent.change(screen.getByLabelText('Email'), {
    target: { value: 'hero@example.com' },
  })
  fireEvent.change(screen.getByLabelText('Password'), {
    target: { value: 'longpassword' },
  })
  fireEvent.submit(screen.getByText('Upgrade account').closest('form')!)
  await waitFor(() =>
    expect(screen.queryByText('Upgrade account')).not.toBeInTheDocument(),
  )
  fireEvent.submit(screen.getByText('Depart Tutorial Island').closest('form')!)
  await waitFor(() => expect(calls).toHaveLength(4))
  expect(calls.map((path) => new URL(path).pathname)).toEqual([
    '/tutorial/depart',
    '/auth/upgrade',
    '/players/me',
    '/tutorial/depart',
  ])
  vi.restoreAllMocks()
})
