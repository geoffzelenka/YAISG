import { useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import type { CharacterProfile } from '../../api/characters'
import { ApiError } from '../../api/http'
import { useRealmMap } from '../../api/realms'
import {
  quoteMarket,
  useMarket,
  useMarketTransfer,
  type Quote,
  type TradeIntent,
} from '../../api/realmMarket'
import { selectorLabel } from '../realm/presentation'

function formatMarketError(cause: unknown): string {
  if (cause instanceof ApiError) return `${cause.message} (${cause.code})`
  return cause instanceof Error ? cause.message : 'Market request failed.'
}

export function RealmMarketPanel({ profile }: { profile: CharacterProfile }) {
  const [search, setSearch] = useSearchParams()
  const map = useRealmMap()
  const id = search.get('realm') || profile.character.current_realm_id
  return (
    <section>
      <h2 className="text-3xl font-bold">Realm market</h2>
      <label>
        Market realm
        <select
          value={id}
          onChange={(event) => setSearch({ realm: event.target.value })}
        >
          {map.data?.nodes.map((node) => (
            <option key={node.realm_id} value={node.realm_id}>
              {node.name}
            </option>
          ))}
        </select>
      </label>
      {map.isError && <p role="alert">Unable to load realms.</p>}
      <MarketView
        key={id}
        id={id}
        present={id === profile.character.current_realm_id}
      />
    </section>
  )
}
function MarketView({ id, present }: { id: string; present: boolean }) {
  const market = useMarket(id)
  const [intent, setIntent] = useState<TradeIntent>({
    item_id: '',
    side: 'sell',
    quantity: 1,
  })
  const [quote, setQuote] = useState<Quote | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const inFlight = useRef<boolean>(false)
  const [busy, setBusy] = useState(false)
  const [gift, setGift] = useState(1)
  const [confirmGift, setConfirmGift] = useState(false)
  const transfer = useMarketTransfer(id)
  async function loadQuote() {
    setSuccess('')
    setQuote(null)
    setBusy(true)
    try {
      setQuote(await quoteMarket(id, intent))
    } catch (cause) {
      setError(formatMarketError(cause))
    } finally {
      setBusy(false)
    }
  }
  async function confirmTrade() {
    if (!quote || !present || inFlight.current) return
    inFlight.current = true
    setError('')
    setSuccess('')
    try {
      const result = await transfer.mutateAsync({
        intent,
        limit_gold: quote.gold,
      })
      if (result) {
        setSuccess(
          `${intent.side === 'buy' ? 'Bought' : 'Sold'} ${result.max_quantity} ${intent.item_id} for ${result.gold} gold.`,
        )
      }
      setQuote(null)
    } catch (cause) {
      setQuote(null)
      if (cause instanceof ApiError && cause.code === 'PRICE_MOVED') {
        setError(
          `${formatMarketError(cause)} Review the new quote and confirm again.`,
        )
        await loadQuote()
      } else setError(formatMarketError(cause))
    } finally {
      inFlight.current = false
    }
  }
  async function sendGift() {
    if (!present || inFlight.current) return
    inFlight.current = true
    setError('')
    setSuccess('')
    try {
      await transfer.mutateAsync({ gold: gift })
      setSuccess(`Gave ${gift} gold to this realm.`)
      setConfirmGift(false)
    } catch (cause) {
      setError(formatMarketError(cause))
    } finally {
      inFlight.current = false
    }
  }
  if (market.isPending) return <p>Loading market…</p>
  if (market.isError)
    return <p role="alert">Unable to load market: {market.error.message}</p>
  const data = market.data
  const items = [
    ...new Set(
      intent.side === 'buy'
        ? data.for_sale.map((sale) => sale.item_id)
        : data.lines.flatMap((line) =>
            line.members.map((member) => member.item_id),
          ),
    ),
  ]
  return (
    <>
      <p>
        {present
          ? 'Present — visitors and residents can trade.'
          : 'Not present — travel here to trade or give gold.'}
      </p>
      {!present && (
        <Link to={`/realm/map?destination=${encodeURIComponent(id)}`}>
          Travel here
        </Link>
      )}
      <p>
        {data.decay_stage} · Gauge: {data.gauge_days.toFixed(2)} days · Treasury
        band: {data.treasury_band ?? 'Unavailable'} (0 poorest–4 richest)
      </p>
      <h3>Demand lines</h3>
      <p>
        Line amounts are line units. Member bids are alternatives sharing one
        budget; quantities below are whole items.
      </p>
      {data.lines.map((line) => (
        <article
          key={line.line_key}
          className="my-4 rounded border border-slate-700 p-4"
        >
          <h4>{selectorLabel(line.selector)}</h4>
          <p>
            Stock: {line.stock / 1000} · Reserve: {line.reserve / 1000} · Cap:{' '}
            {line.cap / 1000} · Cover:{' '}
            {line.days_of_cover === null
              ? 'No upkeep'
              : `${line.days_of_cover.toFixed(2)} days`}
          </p>
          <ul>
            {line.members.map((member) => (
              <li key={member.item_id}>
                {member.item_id}:{' '}
                {member.spot_bid === null
                  ? 'No funded bid'
                  : `Spot bid ${member.spot_bid} gold`}{' '}
                · Funded quantity: {member.funded_quantity} · Total:{' '}
                {member.funded_total} gold
              </li>
            ))}
          </ul>
        </article>
      ))}
      <h3>Items for sale</h3>
      <ul>
        {data.for_sale.map((sale) => (
          <li key={sale.item_id}>
            {sale.item_id}: {sale.quantity} items · Spot ask: {sale.spot_ask}{' '}
            gold
          </li>
        ))}
      </ul>
      <h3>Shortfalls</h3>
      <ul aria-label="Shortfalls">
        {data.shortfalls.map((short) => (
          <li key={short.line_key}>
            {selectorLabel(
              data.lines.find((line) => line.line_key === short.line_key)
                ?.selector ?? { item: short.line_key },
            )}
            : missing {short.missing_milli / 1000} line units (unfunded)
          </li>
        ))}
      </ul>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          setError('')
          void loadQuote()
        }}
      >
        <fieldset
          disabled={busy || transfer.isPending}
          onChange={() => setQuote(null)}
        >
          <legend>Trade with realm</legend>
          <label>
            Side
            <select
              value={intent.side}
              onChange={(e) => {
                setIntent({
                  ...intent,
                  side: e.target.value as TradeIntent['side'],
                  item_id: '',
                })
                setQuote(null)
              }}
            >
              <option value="sell">Sell to realm</option>
              <option value="buy">Buy from realm</option>
            </select>
          </label>
          <label>
            Item
            <select
              required
              value={intent.item_id}
              onChange={(e) =>
                setIntent({ ...intent, item_id: e.target.value })
              }
            >
              <option value="">Choose item</option>
              {items.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>
          <label>
            Quantity
            <input
              type="number"
              min="1"
              step="1"
              required
              value={intent.quantity}
              onChange={(e) =>
                setIntent({ ...intent, quantity: Number(e.target.value) })
              }
            />
          </label>
          <button className="secondary-button" disabled={!intent.item_id}>
            Get quote
          </button>
        </fieldset>
      </form>
      {quote && (
        <div role="status">
          <p>
            {intent.side === 'buy' ? 'Pay' : 'Receive'} {quote.gold} gold for{' '}
            {intent.quantity} {intent.item_id}. Maximum tradable:{' '}
            {quote.max_quantity} items. Your holdings are checked on
            confirmation.
          </p>
          <button
            className="primary-button"
            disabled={
              !present ||
              busy ||
              transfer.isPending ||
              intent.quantity > quote.max_quantity
            }
            onClick={() => void confirmTrade()}
          >
            Confirm trade
          </button>
        </div>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          setConfirmGift(true)
        }}
      >
        <label>
          Treasury gift
          <input
            type="number"
            min="1"
            step="1"
            required
            value={gift}
            onChange={(e) => {
              setGift(Number(e.target.value))
              setConfirmGift(false)
            }}
          />
        </label>
        <button
          className="secondary-button"
          disabled={!present || transfer.isPending}
        >
          Give gold
        </button>
      </form>
      {confirmGift && (
        <div role="dialog" aria-label="Confirm treasury gift">
          <p>Give {gift} gold to this realm?</p>
          <button
            disabled={!present || transfer.isPending}
            onClick={() => void sendGift()}
          >
            Confirm gift
          </button>
          <button onClick={() => setConfirmGift(false)}>Cancel</button>
        </div>
      )}
      {success && <p role="status">{success}</p>}
      {error && <p role="alert">{error}</p>}
    </>
  )
}
