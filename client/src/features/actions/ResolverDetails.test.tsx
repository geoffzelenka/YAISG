import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { emptyRewards } from '../../api/actions'
afterEach(cleanup)

import { WelcomeBack } from './ActionExperience'
import { JourneyProgress, ResolverDetails } from './ResolverDetails'

it('renders journey progress from server meta', () => {
  render(
    <JourneyProgress
      active={{
        action_id: 'any',
        cycle_ms: 5000,
        started_at: '',
        last_resolved_at: '',
        meta: {
          route: [{ edge_id: 'first' }, { edge_id: 'second' }],
          step_index: 1,
          remaining_ms: 2000,
        },
      }}
    />,
  )
  expect(
    screen.getByText('Journey step 2 of 2 · Current edge: second'),
  ).toBeInTheDocument()
})
it('shows welcome-back travel summary and supplies, preserving unknown details', () => {
  render(
    <WelcomeBack
      rewards={{
        ...emptyRewards(),
        items_consumed: { ration: 4 },
        details: {
          resolutions: [
            {
              edges_completed: ['road', 'bridge'],
              current_realm_id: 'b',
              supplies_used: { ration: 4 },
              xp: 12,
              level_ups: {},
              stop_reason: null,
              weather: 'Clear skies',
            },
            { encounter: { outcome: 'survived' } },
          ],
        },
      }}
      names={{
        itemNames: new Map(),
        skillNames: new Map(),
        realmNames: new Map([['b', 'Test Harbor']]),
      }}
      onClose={() => {}}
    />,
  )
  expect(screen.getByRole('dialog')).toHaveTextContent(
    'Travel: 2 edges completed · Current realm: Test Harbor',
  )
  expect(screen.getByText('4 ration consumed')).toBeInTheDocument()
  expect(screen.getByText('survived')).toBeInTheDocument()
  expect(screen.getByText('Clear skies')).toBeInTheDocument()
  for (const label of [
    'supplies used',
    'xp',
    'level ups',
    'stop reason',
    'current realm id',
    'edges completed',
  ]) {
    expect(screen.queryByText(label, { exact: true })).not.toBeInTheDocument()
  }
})
it('renders generic reward details in resolution order', () => {
  const { container } = render(
    <ResolverDetails
      details={{ resolutions: [{ custom: 'first' }, { custom: 'second' }] }}
    />,
  )
  expect(container.textContent).toBe('customfirstcustomsecond')
})

it.each(['OUT_OF_AMMO', 'DEFEATED', 'OFFLINE_CAP'])(
  'renders offline combat summary and %s',
  (reason) => {
    render(
      <WelcomeBack
        rewards={{
          ...emptyRewards(),
          cycles_completed: 20,
          xp_gained: { melee: 32 },
          items_consumed: { food: 2 },
          items_gained: { loot: 3 },
          stop_reason: reason,
          details: {
            resolutions: [
              {
                kills: 4,
                defeats: reason === 'DEFEATED' ? 1 : 0,
                damage_dealt: 123,
                damage_taken: 40,
                xp_by_skill: { melee: 32 },
                consumables_used: { food: 2 },
                loot: { loot: 3 },
              },
            ],
          },
        }}
        onClose={() => {}}
      />,
    )
    const modal = screen.getByRole('dialog')
    expect(modal).toHaveTextContent('Combat summary')
    expect(modal).toHaveTextContent('kills4')
    expect(modal).toHaveTextContent('damage dealt123')
    expect(modal).toHaveTextContent('damage taken40')
    expect(modal).toHaveTextContent('2 food consumed')
    expect(modal).toHaveTextContent('melee XP: 32')
    expect(modal).toHaveTextContent(`Stopped: ${reason}`)
  },
)
