import { render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'

import { ProfilePanel } from './App'
import type { CharacterProfile } from './api/characters'

vi.mock('./api/realms', () => ({ useRealm: () => ({ data: undefined }) }))
vi.mock('./api/content', () => ({ useContent: () => ({ status: 'loading' }) }))
vi.mock('./features/profile/InventoryPanel', () => ({
  InventoryPanel: () => null,
}))

it('shows Maximum level when XP to next is null', () => {
  const profile: CharacterProfile = {
    character: { id: 'c', name: 'Hero', current_realm_id: 'r', created_at: '' },
    skills: [
      {
        id: 'gathering',
        name: 'Gathering',
        xp: 10_000_000,
        level: 100,
        xp_into_level: 0,
        xp_to_next: null,
        tier: 5,
        tier_title: 'Placeholder',
      },
    ],
    gold: 0,
    realm: { id: 'r', name: 'Realm', tags: [], active_modifiers: [] },
    estate: { id: 'e', tier: 1, upgrade_slots: 2, installed_upgrades: [] },
    caps: {
      offline_hours: { base: 12, effective: 12 },
      inventory_slots: { base: 30, effective: 30 },
      order_slots: { base: 5, effective: 5 },
      key_listings: { base: 2, effective: 2 },
      belt_slots: { base: 2, effective: 2 },
      estate_upgrade_slots: { base: 2, effective: 2 },
    },
  }
  render(<ProfilePanel profile={profile} />)
  expect(screen.getByText('Maximum level')).toBeInTheDocument()
  expect(screen.queryByText(/to next/)).not.toBeInTheDocument()
})
