import { useMutation } from '@tanstack/react-query'
import type { ActionFeedResponse } from './actions'
import type { Selector } from './content'
import { gameRequest, readApiError } from './http'

export type TravelRequest = {
  destination_realm_id: string
  mode: 'visit' | 'relocate'
}
export type TravelPreview = {
  route: {
    edge_id: string
    destination_realm_id: string
    time_ms: number
    supplies: { selector: Selector; quantity: number }[]
  }[]
}
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await gameRequest(path, init)
  if (!response.ok) {
    const error = await readApiError(response, 'Travel request failed')
    throw new Error(error.message)
  }
  return (await response.json()) as T
}
export function useTravelPreview() {
  return useMutation({
    mutationFn: (input: TravelRequest) =>
      request<TravelPreview>(
        `/travel/preview?${new URLSearchParams(input).toString()}`,
      ),
  })
}
export function useStartTravel() {
  return useMutation({
    mutationFn: (input: TravelRequest) =>
      request<ActionFeedResponse>('/travel/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      }),
    onSuccess: (feed) => {
      window.dispatchEvent(
        new CustomEvent('yaisg:travel-started', { detail: feed }),
      )
    },
  })
}
