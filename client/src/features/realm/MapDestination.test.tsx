import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import type { CharacterProfile } from '../../api/characters'
import type { Content } from '../../api/content'
import type { Estate } from '../../api/estates'
import { EstateLifecycle } from '../estate/EstateLifecycle'
import { MapPanel } from './MapPanel'

vi.mock('../../api/content', () => ({
  useContent: () => ({ status: 'loading' }),
}))
const profile = { character: { current_realm_id: 'away' } } as CharacterProfile
const estate = {
  realm_id: 'home',
  gauge: 0,
  decay_stage: 'fed',
  surrender_value: 42,
  form: { id: 'house', name: 'Home House', mobility: 'fixed' },
  installed_upgrades: [],
  larder: {},
} as unknown as Estate
vi.mock('../../api/characters', () => ({
  useCharacterProfile: () => ({ data: profile }),
}))
vi.mock('../../api/estates', () => ({ useEstate: () => ({ data: estate }) }))
vi.mock('../../api/inventory', () => ({
  useInventory: () => ({ data: { items: [] } }),
}))
vi.mock('../../api/realms', () => ({
  useRealmMap: () => ({
    isPending: false,
    isError: false,
    data: {
      nodes: [
        { realm_id: 'away', name: 'Away', position: null, gauge: 0 },
        { realm_id: 'home', name: 'Home', position: null, gauge: 0 },
      ],
      edges: [],
    },
  }),
}))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  profile.character.current_realm_id = 'away'
})

it('estate travel link preselects the home realm on the map without reloading', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn((path: string) =>
      Promise.resolve(
        new Response(path.endsWith('/market') ? '{"lines":[]}' : '[]'),
      ),
    ),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={['/estate']}>
        <Routes>
          <Route
            path="/estate"
            element={
              <EstateLifecycle
                estate={estate}
                content={
                  {
                    estate_forms: { forms: [] },
                    items: { items: [] },
                  } as unknown as Content
                }
              />
            }
          />
          <Route path="/realm/map" element={<MapPanel profile={profile} />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  fireEvent.click(
    screen.getByRole('link', { name: 'Travel to estate realm home' }),
  )
  expect(await screen.findByLabelText('Destination')).toHaveValue('home')
  expect(screen.getByRole('button', { name: 'Preview journey' })).toBeEnabled()
})

it('surrender confirmation shows an uncapped upper bound and donation stays explicit', () => {
  vi.stubGlobal(
    'fetch',
    vi.fn((path: string) =>
      Promise.resolve(
        new Response(path.endsWith('/market') ? '{"lines":[]}' : '[]'),
      ),
    ),
  )
  profile.character.current_realm_id = 'home'
  const view = render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <EstateLifecycle
          estate={estate}
          content={
            {
              estate_forms: { forms: [] },
              items: { items: [] },
            } as unknown as Content
          }
        />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Surrender for payout' }))
  expect(screen.getByRole('dialog')).toHaveTextContent(
    'Up to 42 gold; the realm pays less if its treasury cannot cover it; rechecked on surrender',
  )
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
  fireEvent.click(screen.getByRole('button', { name: 'Donate estate' }))
  expect(screen.getByRole('dialog')).toHaveTextContent('Donation: no payout.')
  expect(screen.getByRole('dialog')).not.toHaveTextContent('Up to')
  view.unmount()
  profile.character.current_realm_id = 'away'
})

it.each(['away', 'hidden'])(
  'does not preselect invalid travel destination %s',
  (destination) => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter
          initialEntries={[`/realm/map?destination=${destination}`]}
        >
          <MapPanel profile={profile} />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByLabelText('Destination')).toHaveValue('')
    expect(
      screen.getByRole('button', { name: 'Preview journey' }),
    ).toBeDisabled()
  },
)
