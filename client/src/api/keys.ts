import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { Action } from './content'
import { ApiError, gameRequest, readApiError } from './http'

export type KeyInstance = {
  id: string
  template_id: string
  discovered_by_name: string
  realm_id: string
  payload: { action: Action; [key: string]: unknown }
  uses_total: number
  uses_remaining: number
  state: string
  bound_at: string | null
}
export type KeyListing = {
  id: string
  key: KeyInstance
  price_gold: number
  deprecated: boolean
  status: string
}
export async function keyRequest<T>(
  path: string,
  method = 'GET',
  body?: unknown,
): Promise<T> {
  const response = await gameRequest(path, {
    method,
    ...(body === undefined
      ? {}
      : {
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }),
  })
  if (!response.ok) {
    const error = await readApiError(response, 'Request failed')
    throw new ApiError(error.code ?? 'REQUEST_FAILED', error.message)
  }
  return response.status === 204
    ? (undefined as T)
    : ((await response.json()) as T)
}
export function useKeys() {
  return useQuery({
    queryKey: ['keys'],
    queryFn: () => keyRequest<{ keys: KeyInstance[] }>('/keys/me'),
  })
}
export function useKeyChange() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({
      path,
      method,
      body,
    }: {
      path: string
      method: string
      body?: unknown
    }) => keyRequest(path, method, body),
    onSuccess: async () => {
      await client.invalidateQueries()
      window.dispatchEvent(new Event('yaisg:action-changed'))
    },
  })
}
