import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { ApiError, gameRequest, readApiError } from './http'

export type OrderIntent = {
  side: 'buy' | 'sell'
  item_id: string
  quantity: number
  unit_price: number
}
export type Order = OrderIntent & {
  id: string
  quantity_remaining: number
  escrow_gold_remaining: number
  fill_items: number
  fill_gold: number
  status: 'open' | 'collectable' | 'closed'
  realm_id: string
  created_at: string
  expires_at: string
  closed_at: string | null
}
export type Fill = {
  id: string
  side: 'buy' | 'sell'
  item_id: string
  quantity: number
  unit_price: number
  tax_gold: number
  burned_gold: number
  tax_realm_id: string
  matched_at: string
}
export type MarketResult = {
  order: Order
  fills?: Fill[]
  collected?: { items: number; gold: number }
}
async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await gameRequest(
    `/market/${path}`,
    body === undefined
      ? undefined
      : {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        },
  )
  if (!response.ok) {
    const error = await readApiError(response, 'Market request failed')
    throw new ApiError(error.code ?? 'MARKET_REQUEST_FAILED', error.message)
  }
  return response.json() as Promise<T>
}
export function useBook(item: string, depth: number) {
  return useQuery({
    queryKey: ['global-market', 'book', item, depth],
    queryFn: () =>
      request<{
        buy: { unit_price: number; quantity: number }[]
        sell: { unit_price: number; quantity: number }[]
      }>(`book/${encodeURIComponent(item)}?depth=${depth}`),
    enabled: !!item,
    refetchInterval: 30_000,
  })
}
export function useOrders() {
  return useQuery({
    queryKey: ['global-market', 'orders'],
    queryFn: () => request<{ orders: Order[] }>('orders/me'),
    refetchInterval: 30_000,
  })
}
export function useHistory() {
  return useInfiniteQuery({
    queryKey: ['global-market', 'history'],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) =>
      request<{ matches: Fill[]; next_cursor: string | null }>(
        `history/me?limit=50${pageParam ? `&before=${encodeURIComponent(pageParam)}` : ''}`,
      ),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  })
}
export function useOrderTransfer(currentRealmId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (
      intent: OrderIntent | { id: string; action: 'collect' | 'cancel' },
    ) =>
      'action' in intent
        ? request<MarketResult>(
            `orders/${encodeURIComponent(intent.id)}/${intent.action}`,
            {},
          )
        : request<MarketResult>('orders', intent),
    retry: false,
    onError: async () => {
      await client.invalidateQueries({ queryKey: ['realms', currentRealmId] })
    },
    onSuccess: async () => {
      await Promise.all(
        ['global-market', 'characters', 'realms', 'estates', 'map'].map((key) =>
          client.invalidateQueries({ queryKey: [key] }),
        ),
      )
    },
  })
}
