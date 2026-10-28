import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useContent } from '../../api/content'
import {
  keyRequest,
  useKeys,
  useKeyChange,
  type KeyInstance,
  type KeyListing,
} from '../../api/keys'

export function KeyDetails({
  value,
  deprecated = false,
}: {
  value: KeyInstance
  deprecated?: boolean
}) {
  const content = useContent()
  const action = value.payload.action
  const name =
    content.status === 'ready'
      ? content.content.exploration.templates.find(
          (template) => template.id === value.template_id,
        )?.name
      : undefined
  return (
    <div>
      <h3>
        {typeof value.payload.name === 'string'
          ? value.payload.name
          : (name ?? action.name ?? value.template_id)}
      </h3>
      <span role="status">{value.state}</span>
      {value.bound_at && <span> · Bound</span>}
      {(deprecated || value.state === 'deprecated') && (
        <strong> · Deprecated: realm transition pending</strong>
      )}
      <p>
        Discovered by {value.discovered_by_name} · Realm: {value.realm_id}
      </p>
      <p>
        Uses: {value.uses_remaining} / {value.uses_total}
      </p>
      {typeof value.payload.flavour === 'string' && (
        <p>{value.payload.flavour}</p>
      )}
      {action.resolver !== 'combat' && (
        <p>
          Cycle:{' '}
          {action.base_cycle_ms ? `${action.base_cycle_ms / 1000}s` : 'Combat'}{' '}
          · XP: {action.xp} · Level: {action.unlock_level}
        </p>
      )}
      {action.requires?.tool_class && (
        <p>Tool required: {action.requires.tool_class}</p>
      )}
      {action.combatant_id && (
        <p>
          Combatant:{' '}
          {content.status === 'ready'
            ? (content.content.combatants.combatants.find(
                (entry) => entry.id === action.combatant_id,
              )?.name ?? action.combatant_id)
            : action.combatant_id}
        </p>
      )}
      {action.outputs?.map((drop) => (
        <p key={drop.item_id}>
          {drop.quantity_min}–{drop.quantity_max} ×{' '}
          {content.status === 'ready'
            ? (content.content.items.items.find(
                (entry) => entry.id === drop.item_id,
              )?.name ?? drop.item_id)
            : drop.item_id}{' '}
          ({drop.chance * 100}%)
        </p>
      ))}
    </div>
  )
}
export function KeysPanel() {
  const keys = useKeys()
  const change = useKeyChange()
  const [price, setPrice] = useState(1)
  const [instance, setInstance] = useState('')
  const [filters, setFilters] = useState({
    realm_id: '',
    goods_class: '',
    item_id: '',
    kind: '',
  })
  const [before, setBefore] = useState('')
  const [history, setHistory] = useState<string[]>([])
  const params = new URLSearchParams(
    Object.entries({
      realm_id: filters.realm_id,
      class: filters.goods_class,
      item_id: filters.item_id,
      kind: filters.kind,
      before,
    }).filter(([, value]) => value),
  )
  const market = useQuery({
    queryKey: ['key-market', filters, before],
    queryFn: () =>
      keyRequest<{ listings: KeyListing[]; next_cursor: string | null }>(
        `/keys/market?${params.toString()}`,
      ),
  })
  return (
    <section>
      <h2 className="text-3xl font-bold">Keys</h2>
      {keys.isPending && <p>Loading keys…</p>}
      {keys.error && <p role="alert">{keys.error.message}</p>}
      {keys.data?.keys.length === 0 && <p>No held keys.</p>}
      {keys.data?.keys.map((key) => (
        <article
          className="my-4 rounded border border-slate-700 p-4"
          key={key.id}
        >
          <KeyDetails value={key} />
          <button
            className="primary-button"
            disabled={
              change.isPending ||
              !['active', 'deprecated'].includes(key.state) ||
              !key.uses_remaining
            }
            onClick={() =>
              change.mutate({
                path: '/actions/start',
                method: 'POST',
                body: { key_id: key.id },
              })
            }
          >
            Start {key.payload.action.name}
          </button>
          <button
            className="secondary-button"
            disabled={change.isPending}
            onClick={() => {
              if (window.confirm('Permanently destroy this key?'))
                change.mutate({ path: `/keys/${key.id}`, method: 'DELETE' })
            }}
          >
            Destroy key
          </button>
        </article>
      ))}
      <h3>List a key</h3>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          change.mutate({
            path: '/keys/market',
            method: 'POST',
            body: { instance_id: instance, price_gold: price },
          })
        }}
      >
        <label>
          Unused key
          <select
            className="auth-input"
            required
            value={instance}
            onChange={(event) => setInstance(event.target.value)}
          >
            <option value="">Choose key</option>
            {keys.data?.keys
              .filter(
                (key) =>
                  key.state === 'active' &&
                  !key.bound_at &&
                  key.uses_remaining === key.uses_total,
              )
              .map((key) => (
                <option key={key.id} value={key.id}>
                  {key.payload.action.name} · {key.id}
                </option>
              ))}
          </select>
        </label>
        <label>
          Price in gold
          <input
            className="auth-input"
            type="number"
            min={1}
            step={1}
            required
            value={price}
            onChange={(event) => setPrice(Number(event.target.value))}
          />
        </label>
        <button className="primary-button" disabled={change.isPending}>
          List key
        </button>
      </form>
      {change.error && (
        <p role="alert">
          {change.error.message}
          {'code' in change.error ? ` (${String(change.error.code)})` : ''}
        </p>
      )}
      <h3>Key market</h3>
      {Object.entries(filters).map(([name, value]) => (
        <label key={name}>
          {name.replaceAll('_', ' ')}
          {name === 'kind' ? (
            <select
              className="auth-input"
              value={value}
              onChange={(event) => {
                setFilters({ ...filters, kind: event.target.value })
                setBefore('')
                setHistory([])
              }}
            >
              <option value="">All</option>
              <option value="gather">Gather</option>
              <option value="combat">Combat</option>
            </select>
          ) : (
            <input
              className="auth-input"
              value={value}
              onChange={(event) => {
                setFilters({ ...filters, [name]: event.target.value })
                setBefore('')
                setHistory([])
              }}
            />
          )}
        </label>
      ))}
      {market.isPending && <p>Loading key market…</p>}
      {market.error && <p role="alert">{market.error.message}</p>}
      {market.data?.listings.map((listing) => (
        <article key={listing.id} className="my-4 border border-slate-700 p-4">
          <KeyDetails value={listing.key} deprecated={listing.deprecated} />
          <p>{listing.price_gold} gold</p>
          <button
            className="primary-button"
            disabled={change.isPending}
            onClick={() =>
              change.mutate({
                path: `/keys/market/${listing.id}/buy`,
                method: 'POST',
                body: { price_gold: listing.price_gold },
              })
            }
          >
            Buy key
          </button>
          <button
            className="secondary-button"
            disabled={change.isPending}
            onClick={() =>
              change.mutate({
                path: `/keys/market/${listing.id}/cancel`,
                method: 'POST',
              })
            }
          >
            Cancel listing (owner only)
          </button>
        </article>
      ))}
      <button
        disabled={!history.length}
        onClick={() => {
          setBefore(history.at(-1) ?? '')
          setHistory(history.slice(0, -1))
        }}
      >
        Previous page
      </button>
      <button
        disabled={!market.data?.next_cursor}
        onClick={() => {
          setHistory([...history, before])
          setBefore(market.data?.next_cursor ?? '')
        }}
      >
        Next page
      </button>
    </section>
  )
}
