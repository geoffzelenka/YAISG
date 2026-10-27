import { useQuery } from '@tanstack/react-query'

import type { ProjectRun } from './development'
import type { MapEdge, Modifier, Selector } from './content'
import { gameRequest, readApiError } from './http'

export type RealmDemandLine = {
  line_key: string
  selector: Selector
  value_measured: boolean
  draw_per_day: number
  reserve: number
  cap: number
  stock: number
  in_transit: number
  below_reserve: boolean
}

export type RealmDetail = {
  active_run: ProjectRun | null
  lines: RealmDemandLine[]
  id: string
  name: string
  node: {
    id: string
    name: string
    realm_type: string
    tier: number
    tags: string[]
    modifiers: Modifier[]
    cap_bonuses: { cap: string; value: number }[]
  }
  pending_transition: {
    to_node: string
    cause: 'upgrade' | 'regression'
    started_at: string
    completes_at: string
  } | null
  tags: { tag_id: string; seq: number; node_id: string }[]
  active_tags: string[]
  decay_stage: string
  gauge: number
}

export type RealmMap = {
  nodes: {
    realm_id: string
    node: string
    tier: number
    decay_stage: string
    gauge: number
    treasury_band: string | null
    transition_pending: boolean
    name: string
    position: { x: number; y: number } | null
  }[]
  edges: MapEdge[]
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
    refetchInterval: 30_000,
  })
}

export function useRealmMap() {
  return useQuery({
    queryKey: ['map'],
    queryFn: () => request<RealmMap>('/map'),
    refetchInterval: 30_000,
  })
}
