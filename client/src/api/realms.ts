import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { ItemQuantity, MapEdge, Modifier } from './content'
import { gameRequest, readApiError } from './http'

export type RealmDetail = {
  id: string
  name: string
  node: {
    id: string
    name: string
    tags: string[]
    modifiers: Modifier[]
    cap_bonuses: { cap: string; value: number }[]
  }
  pending_transition: { to_node_id: string; completes_at: string } | null
  active_projects: {
    project_id: string
    name: string
    targets: ItemQuantity[]
    contribution_totals: Record<string, number>
  }[]
  outgoing_edges: { edge_id: string; progress: number; target: number }[]
}

export type RealmMap = {
  nodes: {
    realm_id: string
    node: string
    tier: number
    decay_stage: string
    treasury_band: string | null
    transition_pending: boolean
    name: string
    position: { x: number; y: number } | null
  }[]
  edges: MapEdge[]
}

export type ContributionResponse = {
  accepted_quantity: number
  project: RealmDetail['active_projects'][number]
  completed: boolean
}

export class RealmApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await gameRequest(path, init)
  if (!response.ok) {
    const error = await readApiError(response, 'Realm request failed')
    throw new RealmApiError(error.code ?? 'REALM_REQUEST_FAILED', error.message)
  }
  return (await response.json()) as T
}

export function useRealm(realmId: string) {
  return useQuery({
    queryKey: ['realms', realmId],
    queryFn: () =>
      request<RealmDetail>(`/realms/${encodeURIComponent(realmId)}`),
    enabled: realmId.length > 0,
  })
}

export function useRealmMap() {
  return useQuery({
    queryKey: ['map'],
    queryFn: () => request<RealmMap>('/map'),
  })
}

export function useContribute(realmId: string, projectId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: { item_id: string; quantity: number }) =>
      request<ContributionResponse>(
        `/realms/${encodeURIComponent(realmId)}/projects/${encodeURIComponent(projectId)}/contribute`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(input),
        },
      ),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: ['realms', realmId] }),
        client.invalidateQueries({
          queryKey: ['characters', 'me', 'inventory'],
        }),
      ])
    },
  })
}
