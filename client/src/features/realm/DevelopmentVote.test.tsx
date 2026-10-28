import {
  MutationObserver as QueryMutationObserver,
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import type { CharacterProfile } from '../../api/characters'
import type { Content } from '../../api/content'
import type { RealmDetail } from '../../api/realms'
import { DevelopmentControls } from './DevelopmentControls'

vi.mock('../../api/estates', () => ({
  useEstate: () => ({ data: { realm_id: 'home' }, isSuccess: true }),
}))
vi.mock('../../api/inventory', () => ({
  useInventory: () => ({ data: { items: [] } }),
}))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

it('resets mutation variables after a successful confirmed vote cast', async () => {
  let voted = false
  const fetch = vi.fn((input: string, init?: RequestInit) => {
    const path = new URL(input).pathname
    if (path.endsWith('/vote') && init?.method === 'POST') voted = true
    const body = path.endsWith('/vote')
      ? {
          id: 'ballot',
          upgrade_id: 'next',
          status: voted ? 'passed' : 'open',
          closes_at: '2099-01-01T00:00:00Z',
          yes_weight: voted ? 1 : null,
          no_weight: voted ? 0 : null,
          participation: [
            {
              character_id: 'player',
              weight: 1,
              voted_at: voted ? '2026-01-01T00:00:00Z' : null,
            },
          ],
        }
      : path.endsWith('/estates')
        ? []
        : {}
    return Promise.resolve(new Response(JSON.stringify(body)))
  })
  vi.stubGlobal('fetch', fetch)
  const reset = vi.spyOn(QueryMutationObserver.prototype, 'reset')
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <DevelopmentControls
          realm={
            {
              id: 'home',
              node: { id: 'node', tags: [] },
              tags: [],
              lines: [],
            } as unknown as RealmDetail
          }
          profile={
            {
              character: { id: 'player', current_realm_id: 'home' },
            } as CharacterProfile
          }
          content={
            {
              development: { nodes: [] },
              combatants: { combatants: [] },
              estate_forms: { forms: [] },
            } as unknown as Content
          }
        />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  fireEvent.click(await screen.findByRole('button', { name: 'Vote yes' }))
  expect(fetch.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(
    false,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))
  await waitFor(() => expect(reset).toHaveBeenCalledOnce())
  expect(
    fetch.mock.calls.find(([, init]) => init?.method === 'POST')?.[1]?.body,
  ).toBe('{"choice":"yes"}')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})
