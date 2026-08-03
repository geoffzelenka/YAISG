import { useQuery } from '@tanstack/react-query'

import { gameRequest } from './http'

export type Player = {
  id: string
  auth_user_id: string
  created_at: string
}

async function getCurrentPlayer(): Promise<Player> {
  const response = await gameRequest('/players/me')
  if (!response.ok) {
    throw new Error('Unable to load player')
  }
  return (await response.json()) as Player
}

export function useCurrentPlayer() {
  return useQuery({ queryKey: ['players', 'me'], queryFn: getCurrentPlayer })
}
