import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { gameRequest, readApiError } from './http'
import type { Selector } from './content'

export type ProjectRun = {
  id: string
  project_id: string
  status: string
  stalled: boolean
  required: { selector: Selector; quantity: number }[]
  contributed: number[]
  build_completes_at: string | null
}
export type Vote = {
  id: string
  upgrade_id: string
  status: string
  closes_at: string
  yes_weight: number | null
  no_weight: number | null
  participation: {
    character_id: string
    weight: number
    voted_at: string | null
  }[]
}
export type RealmEstate = {
  id: string
  owner: string
  form: string
  gauge: number
  decay_stage: string
  sale_price: number | null
}
export type Credits = {
  kicked_off_by: string | null
  contributions: Record<string, number>
  realm_share: number
}
async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await gameRequest(
    path,
    body === undefined
      ? undefined
      : {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        },
  )
  if (!response.ok) {
    const error = await readApiError(response, 'Development request failed')
    throw new Error(`${error.message} (${error.code})`)
  }
  return (await response.json()) as T
}
export function useDevelopmentRead<T>(realmId: string, suffix: string) {
  return useQuery({
    queryKey: ['realms', realmId, suffix],
    queryFn: () =>
      request<T>(`/realms/${encodeURIComponent(realmId)}/${suffix}`),
    enabled: !!realmId,
    refetchInterval: 30_000,
  })
}
export function useDevelopmentAction() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ path, body }: { path: string; body: unknown }) =>
      request<unknown>(path, body),
    onSuccess: async () => {
      await Promise.all(
        ['realms', 'estates', 'characters', 'map'].map((key) =>
          client.invalidateQueries({ queryKey: [key] }),
        ),
      )
    },
  })
}
