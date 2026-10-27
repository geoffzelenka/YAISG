import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import type { Project } from '../../api/content'
import type { RealmDetail } from '../../api/realms'
import { VotePanel } from './DevelopmentControls'
import { kickoffReason } from './kickoffReason'
import { coverDays } from './presentation'

const project = {
  grants_tag: 'built',
  requires_tags: ['ready'],
  kickoff: { who: 'residents' },
} as Project
const realm = {
  node: { tags: ['ready'] },
  tags: [],
  lines: [{ stock: 1 }],
  active_run: null,
  pending_transition: null,
} as unknown as RealmDetail

describe('development presentation', () => {
  it.each([
    [false, false, realm, 'Only residents'],
    [true, true, realm, 'vote is open'],
    [true, false, { ...realm, active_run: {} }, 'project is active'],
    [true, false, { ...realm, pending_transition: {} }, 'transitioning'],
    [true, false, { ...realm, lines: [{ stock: 0 }] }, 'RESERVE_SHORT'],
    [true, false, { ...realm, node: { tags: [] } }, 'Required tags missing'],
    [
      true,
      false,
      { ...realm, tags: [{ tag_id: 'built' }] },
      'Tag already held',
    ],
  ])(
    'kickoff unavailable reasons: %s %s %j',
    (resident, open, snapshot, reason) => {
      expect(
        kickoffReason(project, snapshot as RealmDetail, resident, open),
      ).toContain(reason)
    },
  )
  it('allows stocked eligible kickoff', () => {
    expect(kickoffReason(project, realm, true, false)).toBeNull()
  })
  it('vote panel hides totals while open and exposes participation', () => {
    const cast = vi.fn()
    const props = {
      vote: {
        id: 'vote',
        upgrade_id: 'next',
        status: 'open',
        closes_at: '2099-01-01T00:00:00Z',
        yes_weight: 938,
        no_weight: 721,
        participation: [{ character_id: 'player', weight: 10, voted_at: null }],
      },
      characterId: 'player',
      pending: false,
      onCast: cast,
      onExpire: vi.fn(),
    }
    const view = render(<VotePanel {...props} />)
    expect(
      screen.getByText(/player · weight 10 · Not voted/),
    ).toBeInTheDocument()
    expect(
      screen.queryByText(/938|721|Yes weight|No weight/),
    ).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Vote yes' }))
    expect(cast).toHaveBeenCalledWith('yes')
    view.rerender(
      <VotePanel {...props} vote={{ ...props.vote, status: 'passed' }} />,
    )
    expect(
      screen.getByText(/Yes weight: 938; No weight: 721/),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Vote yes' }),
    ).not.toBeInTheDocument()
  })
  it('larder days of cover uses milli-units and handles empty and upkeep-free larders', () => {
    expect(coverDays(7500, 3)).toBe('2.50 days')
    expect(coverDays(0, 3)).toBe('0.00 days')
    expect(coverDays(500, 0)).toBe('No upkeep')
  })
})
