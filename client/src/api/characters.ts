import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { Modifier } from './content'
import { gameRequest, readApiError } from './http'

export type CharacterProfile = {
  character: {
    id: string
    name: string
    realm_id: string
    created_at: string
  }
  skills: {
    id: string
    name: string
    xp: number
    level: number
    xp_into_level: number
    xp_to_next: number | null
    tier: number
    tier_title: string
  }[]
  gold: number
  realm: {
    id: string
    name: string
    tags: string[]
    active_modifiers: Modifier[]
  }
  caps: Record<
    | 'offline_hours'
    | 'inventory_slots'
    | 'order_slots'
    | 'key_listings'
    | 'belt_slots'
    | 'estate_upgrade_slots',
    { base: number; effective: number }
  >
  estate: {
    id: string
    level: number
    upgrade_slots: number
    installed_upgrades: { slot_index: number; upgrade_id: string }[]
  }
}

export class CharacterApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message)
  }
}

async function profileRequest(): Promise<CharacterProfile | null> {
  const response = await gameRequest('/characters/me')
  if (response.status === 404) {
    const error = await readApiError(
      response,
      'Unable to load character profile',
    )
    if (error.code === 'NO_CHARACTER') return null
  }
  if (!response.ok) throw new Error('Unable to load character profile')
  return (await response.json()) as CharacterProfile
}

async function createCharacter(input: {
  name: string
  realm_id: string
}): Promise<CharacterProfile> {
  const response = await gameRequest('/characters', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!response.ok) {
    const error = await readApiError(response, 'Unable to create character')
    throw new CharacterApiError(error.code ?? 'CREATE_FAILED', error.message)
  }
  return (await response.json()) as CharacterProfile
}

export function useCharacterProfile() {
  return useQuery({ queryKey: ['characters', 'me'], queryFn: profileRequest })
}

export function useCreateCharacter() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createCharacter,
    onSuccess: (profile) =>
      queryClient.setQueryData(['characters', 'me'], profile),
  })
}
