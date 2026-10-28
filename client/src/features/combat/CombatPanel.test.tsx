import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type { CharacterProfile } from '../../api/characters'
import { CombatPanel } from './CombatPanel'

vi.mock('../equipment/EquipmentPanel', () => ({
  ConsumablesPanel: () => <p>Consumable setup</p>,
}))
vi.mock('../../api/content', () => ({
  useContent: () => ({
    status: 'ready',
    content: {
      skills: {
        skills: [
          {
            actions: [
              {
                id: 'fight',
                name: 'Fight',
                resolver: 'combat',
                combatant_id: 'dummy',
                location: 'Arena',
              },
            ],
          },
        ],
      },
      combatants: { combatants: [{ id: 'dummy', name: 'Dummy' }] },
      progression: {
        stances: {
          balanced: { style: 0.5, accuracy: 0.5 },
          precise: { style: 0.25, accuracy: 0.75 },
        },
      },
    },
  }),
}))
vi.mock('../../api/http', async (original) => ({
  ...(await original<typeof import('../../api/http')>()),
  gameRequest: (path: string, init?: RequestInit) => fetch(path, init),
}))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})
it('uses server encounter availability, HP and stance and retains poll log entries', async () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  client.setQueryData(['characters', 'me', 'action'], {
    active: null,
    since_last: { details: { resolutions: [{ kills: 2, damage_dealt: 75 }] } },
    stop_reason: null,
  })
  const request = vi.fn(async (path: string) => {
    await Promise.resolve()
    if (path === '/actions/available')
      return Response.json({
        skills: [
          {
            actions: [
              {
                action_id: 'fight',
                startable: true,
                blocked_by: [],
                cycle_ms: 2345,
              },
            ],
          },
        ],
      })
    if (path === '/actions/start')
      return Response.json({
        action_id: 'fight',
        cycle_ms: 2345,
        started_at: '2030-01-01',
      })
    return Response.json({ stance: 'precise' })
  })
  vi.stubGlobal('fetch', request)
  render(
    <QueryClientProvider client={client}>
      <CombatPanel
        profile={
          {
            character: { stance: 'balanced' },
            hp: 45,
            max_hp: 120,
          } as CharacterProfile
        }
      />
    </QueryClientProvider>,
  )
  expect(
    screen.getByRole('progressbar', { name: 'Hit points' }),
  ).toHaveAttribute('value', '45')
  expect(screen.getByLabelText('Stance')).toHaveValue('balanced')
  expect(await screen.findByText('Arena')).toBeInTheDocument()
  expect(screen.getByText('Dummy')).toBeInTheDocument()
  await waitFor(() => expect(screen.getByText('Start combat')).toBeEnabled())
  fireEvent.click(screen.getByText('Start combat'))
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith(
      '/actions/start',
      expect.objectContaining({ body: JSON.stringify({ action_id: 'fight' }) }),
    ),
  )
  fireEvent.change(screen.getByLabelText('Stance'), {
    target: { value: 'precise' },
  })
  await waitFor(() =>
    expect(request).toHaveBeenCalledWith(
      '/characters/me/stance',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ stance: 'precise' }),
      }),
    ),
  )
  await act(() =>
    client.setQueryData(['characters', 'me', 'action'], {
      active: null,
      since_last: {
        details: { resolutions: [{ kills: 0, damage_dealt: 17 }] },
      },
      stop_reason: 'DEFEATED',
    }),
  )
  await waitFor(() =>
    expect(screen.getByText('Stopped: DEFEATED')).toBeInTheDocument(),
  )
  expect(screen.getByText('75')).toBeInTheDocument()
  expect(screen.getByText('17')).toBeInTheDocument()
})
