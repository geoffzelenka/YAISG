import type { TravelProfile } from './content'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { CapBonus, ItemQuantity, Modifier } from './content'
import { gameRequest, readApiError } from './http'

export type Estate = {
  gauge: number
  larder: Record<string, number>
  surrender_payout: number | null
  id: string
  form: {
    id: string
    name: string
    tags: string[]
    tier: number
    upgrade_slots: number
    mobility: 'mobile' | 'fixed'
    travel_profile: TravelProfile | null
    cap_bonuses: CapBonus[]
    modifiers: Modifier[]
  }
  realm_id: string
  tier: number
  mobility: 'mobile' | 'fixed'
  tags: string[]
  decay_stage: string
  status: string
  upgrade_slots: number
  installed_upgrades: {
    slot_index: number
    upgrade_id: string
    name: string
    status: 'active' | 'inert'
    inert_reason: string | null
  }[]
}

export class EstateApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message)
  }
}

async function estateRequest(
  path: string,
  init?: RequestInit,
): Promise<Estate> {
  const response = await gameRequest(path, init)
  if (!response.ok) {
    const error = await readApiError(response, 'Estate request failed')
    throw new EstateApiError(
      error.code ?? 'ESTATE_REQUEST_FAILED',
      error.message,
    )
  }
  return (await response.json()) as Estate
}

export function useEstate() {
  return useQuery({
    queryKey: ['estates', 'me'],
    queryFn: () => estateRequest('/estates/me'),
  })
}

function useEstateMutation(mutationFn: (value: string) => Promise<Estate>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn,
    onSuccess: async (estate) => {
      client.setQueryData(['estates', 'me'], estate)
      await Promise.all([
        client.invalidateQueries({ queryKey: ['estates', 'me'] }),
        client.invalidateQueries({
          queryKey: ['characters', 'me'],
          exact: true,
        }),
        client.invalidateQueries({
          queryKey: ['characters', 'me', 'inventory'],
        }),
      ])
    },
  })
}

export function usePurchaseUpgrade() {
  return useEstateMutation((upgradeId) =>
    estateRequest(`/estates/me/upgrades/${encodeURIComponent(upgradeId)}`, {
      method: 'POST',
    }),
  )
}

export function useTransformEstate() {
  return useEstateMutation((formId) =>
    estateRequest('/estates/me/transform', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ form_id: formId }),
    }),
  )
}

export function canAfford(
  cost: ItemQuantity[],
  inventory: Map<string, number>,
): boolean {
  return cost.every((entry) => (inventory.get(entry.item_id) ?? 0) >= entry.qty)
}
