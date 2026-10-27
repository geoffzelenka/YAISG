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
            },
            { encounter: { outcome: 'survived' } },
          ],
        },
      }}
      onClose={() => {}}
    />,
  )
  expect(screen.getByRole('dialog')).toHaveTextContent(
    'Travel: 2 edges completed · Current realm: b',
  )
  expect(screen.getByText('4 ration consumed')).toBeInTheDocument()
  expect(screen.getByText('survived')).toBeInTheDocument()
})
it('renders generic reward details in resolution order', () => {
  const { container } = render(
    <ResolverDetails
      details={{ resolutions: [{ custom: 'first' }, { custom: 'second' }] }}
    />,
  )
  expect(container.textContent).toBe('customfirstcustomsecond')
})
