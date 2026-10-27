import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { SkillProgress } from './SkillProgress'

afterEach(cleanup)
it.each([
  [1, 1],
  [9, 1],
  [10, 2],
  [29, 2],
  [30, 3],
  [59, 3],
  [60, 4],
  [89, 4],
  [90, 5],
  [100, 5],
])('shows server tier at level %i', (level, tier) => {
  render(
    <SkillProgress
      skill={{
        id: 'test',
        name: 'Test',
        level,
        tier,
        tier_title: `Title ${tier}`,
        xp: 0,
        xp_into_level: 0,
        xp_to_next: level === 100 ? null : 123,
      }}
    />,
  )
  expect(screen.getByLabelText('Skill tier')).toHaveTextContent(
    `Tier ${tier}: Title ${tier}`,
  )
  expect(
    screen.getByText(level === 100 ? /Maximum level/ : /123 XP to next/),
  ).toBeInTheDocument()
})
