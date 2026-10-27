import { useRef, useState } from 'react'
import type { CharacterProfile } from '../../api/characters'
import { useContent } from '../../api/content'
import { ApiError } from '../../api/http'
import { useRealm } from '../../api/realms'
import {
  useBook,
  useHistory,
  useOrders,
  useOrderTransfer,
  type Fill,
  type OrderIntent,
} from '../../api/globalMarket'

function itemCount(quantity: number): string {
  return `${quantity} ${quantity === 1 ? 'item' : 'items'}`
}

function Executions({
  fills,
  itemName,
}: {
  fills: Fill[]
  itemName: (id: string) => string
}) {
  return (
    <ul>
      {fills.map((fill) => (
        <li key={fill.id}>
          {fill.side} {fill.quantity} {itemName(fill.item_id)} at{' '}
          {fill.unit_price} gold each · Seller tax: {fill.tax_gold} gold ·{' '}
          {fill.matched_at}
        </li>
      ))}
    </ul>
  )
}

export function GlobalMarketPanel({ profile }: { profile: CharacterProfile }) {
  const content = useContent()
  const realm = useRealm(profile.character.current_realm_id)
  const [item, setItem] = useState('')
  const [depth, setDepth] = useState(20)
  const [intent, setIntent] = useState<Omit<OrderIntent, 'item_id'>>({
    side: 'buy',
    quantity: 1,
    unit_price: 1,
  })
  const book = useBook(item, depth)
  const orders = useOrders()
  const history = useHistory()
  const transfer = useOrderTransfer(profile.character.current_realm_id)
  const inFlight = useRef(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [fills, setFills] = useState<Fill[]>([])
  const access =
    content.status === 'ready' &&
    realm.isSuccess &&
    content.content.tags.tags.some(
      (tag) =>
        realm.data.active_tags.includes(tag.id) && tag.effects.market_access,
    )
  async function submit(value: Parameters<typeof transfer.mutateAsync>[0]) {
    if (
      inFlight.current ||
      (!access && (!('action' in value) || value.action === 'collect'))
    )
      return
    inFlight.current = true
    setMessage('')
    setError('')
    setFills([])
    try {
      const result = await transfer.mutateAsync(value)
      if (result.collected) {
        const remaining = result.order.fill_items || result.order.fill_gold
        const waiting = remaining
          ? `Partial collection: ${itemCount(result.order.fill_items)} and ${result.order.fill_gold} gold remain in the slot until capacity is available.`
          : result.order.status === 'open'
            ? 'Nothing is waiting right now.'
            : 'No holdings remain to collect.'
        setMessage(
          `Collected ${itemCount(result.collected.items)} and ${result.collected.gold} gold. ${waiting}`,
        )
      } else if ('action' in value)
        setMessage(
          'Order cancelled. Holdings remain in the slot for collection.',
        )
      else {
        setFills(result.fills ?? [])
        setMessage(
          `Order placed. Remaining on book: ${result.order.quantity_remaining}. Slot holds ${itemCount(result.order.fill_items)} and ${result.order.fill_gold} gold. Collect to move holdings into inventory and wallet.`,
        )
      }
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `${cause.message} (${cause.code})${cause.code === 'MARKET_RETRY' ? ' Please retry the request.' : ''}`
          : cause instanceof Error
            ? cause.message
            : 'Market request failed.',
      )
    } finally {
      inFlight.current = false
    }
  }
  if (content.status !== 'ready')
    return (
      <p>
        {content.status === 'error'
          ? 'Unable to load market content.'
          : 'Loading market content…'}
      </p>
    )
  const itemName = (id: string) =>
    content.content.items.items.find((good) => good.id === id)?.name ?? id
  const marketSettings = content.content.economy.market
  return (
    <section>
      <h2 className="text-3xl font-bold">Player market</h2>
      <p>
        {access
          ? 'Market access available.'
          : realm.isError
            ? 'Unable to verify market access. Creating and collecting are disabled.'
            : realm.isPending
              ? 'Checking market access…'
              : 'No market access in your current realm. Travel to a realm with market access to create orders or collect.'}
      </p>
      <p>
        Books, slots and history are visible everywhere. Cancellation is always
        available.
      </p>
      <label>
        Good
        <select value={item} onChange={(e) => setItem(e.target.value)}>
          <option value="">Choose good</option>
          {content.content.items.items
            .filter((good) => !good.instanced)
            .map((good) => (
              <option key={good.id} value={good.id}>
                {good.name}
              </option>
            ))}
        </select>
      </label>
      <label>
        Book depth
        <select
          value={depth}
          onChange={(e) => setDepth(Number(e.target.value))}
        >
          {[10, 20, 50, 100].map((n) => (
            <option key={n}>{n}</option>
          ))}
        </select>
      </label>
      <h3>Order book</h3>
      {!item ? (
        <p>Choose a good to view its book.</p>
      ) : book.isPending ? (
        <p>Loading book…</p>
      ) : book.isError ? (
        <p role="alert">Unable to load book: {book.error.message}</p>
      ) : (
        (['buy', 'sell'] as const).map((side) => (
          <div key={side}>
            <h4>{side === 'buy' ? 'Bids' : 'Asks'}</h4>
            <table>
              <thead>
                <tr>
                  <th>Unit price (gold)</th>
                  <th>Quantity</th>
                </tr>
              </thead>
              <tbody>
                {book.data[side].map((level) => (
                  <tr key={level.unit_price}>
                    <td>{level.unit_price}</td>
                    <td>{level.quantity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!book.data[side].length && <p>No {side} orders.</p>}
          </div>
        ))
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (item) void submit({ ...intent, item_id: item })
        }}
      >
        <fieldset disabled={!access || transfer.isPending}>
          <legend>Create order</legend>
          <label>
            Side
            <select
              value={intent.side}
              onChange={(e) =>
                setIntent({
                  ...intent,
                  side: e.target.value as OrderIntent['side'],
                })
              }
            >
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </label>
          {(['quantity', 'unit_price'] as const).map((key) => (
            <label key={key}>
              {key === 'quantity' ? 'Quantity' : 'Unit price'}
              <input
                type="number"
                min="1"
                step="1"
                max={Number.MAX_SAFE_INTEGER}
                required
                value={intent[key]}
                onChange={(e) =>
                  setIntent({ ...intent, [key]: Number(e.target.value) })
                }
              />
            </label>
          ))}
          <button disabled={!item}>Place order</button>
        </fieldset>
      </form>
      {marketSettings?.tax_pct !== undefined &&
        marketSettings.order_days !== undefined && (
          <p>
            Orders escrow their full goods or gold. Seller tax:{' '}
            {marketSettings.tax_pct}%. Orders expire after{' '}
            {marketSettings.order_days} days.
          </p>
        )}
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
      {!!fills.length && (
        <div>
          <h3>Immediate fills</h3>
          <Executions fills={fills} itemName={itemName} />
        </div>
      )}
      <h3>Order slots</h3>
      {orders.isPending ? (
        <p>Loading slots…</p>
      ) : orders.isError ? (
        <p role="alert">Unable to load slots: {orders.error.message}</p>
      ) : (
        <>
          <p>
            Slots used:{' '}
            {orders.data.orders.filter((o) => o.status !== 'closed').length} /{' '}
            {profile.caps.order_slots.effective}
          </p>
          {!orders.data.orders.length && <p>No orders.</p>}
          {orders.data.orders.map((order) => (
            <article key={order.id} aria-label={`Order ${order.id}`}>
              <h4>
                {order.side} {itemName(order.item_id)} · {order.status}
              </h4>
              <p>
                Limit: {order.unit_price} gold · Remaining:{' '}
                {order.quantity_remaining} / {order.quantity} · Escrow gold:{' '}
                {order.escrow_gold_remaining}
              </p>
              <p>
                Waiting: {itemCount(order.fill_items)} and {order.fill_gold}{' '}
                gold · Expires: {order.expires_at}
              </p>
              <button
                disabled={
                  !access ||
                  transfer.isPending ||
                  !(order.fill_items || order.fill_gold)
                }
                onClick={() => void submit({ id: order.id, action: 'collect' })}
              >
                Collect
              </button>
              <button
                disabled={transfer.isPending || order.status !== 'open'}
                onClick={() => void submit({ id: order.id, action: 'cancel' })}
              >
                Cancel order
              </button>
            </article>
          ))}
        </>
      )}
      <h3>Trade history</h3>
      {history.isPending ? (
        <p>Loading history…</p>
      ) : (
        <>
          {history.isError && (
            <p role="alert">Unable to load history: {history.error.message}</p>
          )}
          {history.data && (
            <>
              <Executions
                fills={history.data.pages.flatMap((page) => page.matches)}
                itemName={itemName}
              />
              {!history.data.pages[0].matches.length && <p>No trades yet.</p>}
            </>
          )}
          {history.hasNextPage && (
            <button
              disabled={history.isFetchingNextPage}
              onClick={() => void history.fetchNextPage()}
            >
              Load older trades
            </button>
          )}
        </>
      )}
    </section>
  )
}
