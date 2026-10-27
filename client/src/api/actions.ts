import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { gameRequest, readApiError } from './http'

export type AvailableAction = {
  action_id: string
  name: string
  unlock_level: number
  cycle_ms: number
  startable: boolean
  blocked_by: string[]
}
export type AvailableSkill = {
  skill_id: string
  name: string
  actions: AvailableAction[]
}
export type Rewards = {
  cycles_completed: number
  xp_gained: Record<string, number>
  items_consumed: Record<string, number>
  items_gained: Record<string, number>
  overflowed_items: Record<string, number>
  level_ups: Record<string, number[]>
  stop_reason: string | null
  details?: Record<string, unknown>
}
export type ActiveAction = {
  action_id: string
  cycle_ms: number
  started_at: string
  last_resolved_at: string
}
export type ActionFeedResponse = {
  active: ActiveAction | null
  since_last: Rewards
  stop_reason: string | null
}

export class ActionApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message)
  }
}

async function jsonRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await gameRequest(path, init)
  if (!response.ok) {
    const error = await readApiError(
      response,
      `Action request failed (${response.status})`,
    )
    throw new ActionApiError(
      error.code ?? 'ACTION_REQUEST_FAILED',
      error.message,
    )
  }
  return (await response.json()) as T
}

export function useAvailableActions() {
  return useQuery({
    queryKey: ['characters', 'me', 'actions', 'available'],
    queryFn: () =>
      jsonRequest<{ skills: AvailableSkill[] }>('/actions/available'),
  })
}

export function useStartAction() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (actionId: string) =>
      jsonRequest<{ action_id: string; cycle_ms: number; started_at: string }>(
        '/actions/start',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action_id: actionId }),
        },
      ),
    onSuccess: (started) => {
      client.setQueryData<ActionFeedResponse>(['characters', 'me', 'action'], {
        active: { ...started, last_resolved_at: started.started_at },
        since_last: emptyRewards(),
        stop_reason: null,
      })
      void client.invalidateQueries({
        queryKey: ['characters', 'me', 'actions', 'available'],
      })
      window.dispatchEvent(new Event('yaisg:action-changed'))
    },
  })
}

export function useStopAction() {
  return useMutation({
    mutationFn: () =>
      jsonRequest<ActionFeedResponse>('/actions/stop', {
        method: 'POST',
      }),
  })
}

export function fetchAction(): Promise<ActionFeedResponse> {
  return jsonRequest('/actions/poll')
}

export function emptyRewards(): Rewards {
  return {
    cycles_completed: 0,
    xp_gained: {},
    items_consumed: {},
    items_gained: {},
    overflowed_items: {},
    level_ups: {},
    stop_reason: null,
  }
}
