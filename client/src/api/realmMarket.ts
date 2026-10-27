import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import type { Selector } from './content'
import { gameRequest, readApiError } from './http'
import { RealmApiError } from './realms'

export type Market = {
  lines: {
    line_key: string
    selector: Selector
    stock: number
    reserve: number
    cap: number
    draw_per_day: number
    days_of_cover: number | null
    funded_quantity: number
    funded_total: number
    spot_bid: string | null
    members: {
      item_id: string
      spot_bid: string | null
      funded_quantity: number
      funded_total: number
    }[]
  }[]
  for_sale: { item_id: string; quantity: number; spot_ask: number }[]
  shortfalls: { line_key: string; missing_milli: number }[]
  decay_stage: string
  gauge_days: number
  treasury_band: string | null
}
export type TradeIntent = {
  item_id: string
  side: 'buy' | 'sell'
  quantity: number
}
export type Quote = { gold: number; max_quantity: number }
const base = (id: string) => `/realms/${encodeURIComponent(id)}`
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
    const error = await readApiError(response.clone(), 'Market request failed')
    if (error.code === 'UNFUNDED_DEMAND') {
      const payload = (await response.json()) as {
        error?: { max_quantity?: unknown }
      }
      const maximum = payload.error?.max_quantity
      if (
        typeof maximum === 'number' &&
        Number.isSafeInteger(maximum) &&
        maximum >= 0
      ) {
        error.message += ` (Maximum fundable: ${maximum} items)`
      }
    }
    throw new RealmApiError(
      error.code ?? 'MARKET_REQUEST_FAILED',
      error.message,
    )
  }
  return response.status === 204
    ? (undefined as T)
    : ((await response.json()) as T)
}
const marketOptions = (id: string) => ({
  queryKey: ['realms', id, 'market'],
  queryFn: () => request<Market>(`${base(id)}/market`),
  refetchInterval: 30_000,
})
export function useMarket(id: string) {
  return useQuery(marketOptions(id))
}
export function useWorldMarkets(ids: string[]) {
  return useQueries({ queries: ids.map(marketOptions) })
}
export function quoteMarket(id: string, intent: TradeIntent): Promise<Quote> {
  const params = new URLSearchParams({
    ...intent,
    quantity: String(intent.quantity),
  })
  return request<Quote>(`${base(id)}/market/quote?${params.toString()}`)
}
export function useMarketTransfer(id: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (
      transfer: { intent: TradeIntent; limit_gold: number } | { gold: number },
    ) =>
      'intent' in transfer
        ? request<Quote>(`${base(id)}/market/trade`, {
            ...transfer.intent,
            limit_gold: transfer.limit_gold,
          })
        : request<void>(`${base(id)}/treasury/gift`, transfer),
    onSuccess: async () => {
      await Promise.all(
        ['realms', 'characters', 'estates', 'map'].map((key) =>
          client.invalidateQueries({ queryKey: [key] }),
        ),
      )
    },
  })
}
