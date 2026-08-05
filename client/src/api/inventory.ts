import { useQuery } from '@tanstack/react-query'

import { gameRequest } from './http'

export type Inventory = { items: { item_id: string; quantity: number }[] }

export function useInventory() {
  return useQuery({
    queryKey: ['characters', 'me', 'inventory'],
    queryFn: async (): Promise<Inventory> => {
      const response = await gameRequest('/characters/me/inventory')
      if (!response.ok) throw new Error('Unable to load inventory')
      return (await response.json()) as Inventory
    },
  })
}
