import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type ActionFeedResponse, fetchAction } from './actions'
import { ApiError, gameRequest, readApiError } from './http'

export function useActionState() {
  return useQuery<ActionFeedResponse>({
    queryKey: ['characters', 'me', 'action'],
    queryFn: fetchAction,
    enabled: false,
  })
}

/** Setup and stance mutations resolve prior work; refresh every character view. */
export function useEquipmentChange() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async ({
      path,
      body,
      method = 'POST',
    }: {
      path: string
      body: unknown
      method?: 'POST' | 'PUT'
    }) => {
      const response = await gameRequest(path, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!response.ok) {
        const error = await readApiError(response, 'Unable to update equipment')
        throw new ApiError(
          error.code ?? 'EQUIPMENT_REQUEST_FAILED',
          error.message,
        )
      }
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['characters', 'me'] })
      window.dispatchEvent(new Event('yaisg:action-changed'))
    },
  })
}
