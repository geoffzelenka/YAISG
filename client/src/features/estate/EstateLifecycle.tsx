import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { Content } from '../../api/content'
import type { Estate } from '../../api/estates'
import { useCharacterProfile } from '../../api/characters'
import {
  useDevelopmentAction,
  useDevelopmentRead,
  type RealmEstate,
} from '../../api/development'
import { useInventory } from '../../api/inventory'
import { coverDays, matches, selectorLabel } from '../realm/presentation'

export function EstateLifecycle({
  estate,
  content,
}: {
  estate: Estate
  content: Content
}) {
  const profile = useCharacterProfile()
  const inventory = useInventory()
  const current = profile.data?.character.current_realm_id ?? ''
  const estates = useDevelopmentRead<RealmEstate[]>(current, 'estates')
  const action = useDevelopmentAction()
  const [confirm, setConfirm] = useState<{
    path: string
    body: unknown
    message: string
  } | null>(null)
  const [itemId, setItemId] = useState('')
  const [quantity, setQuantity] = useState(1)
  const present = current === estate.realm_id
  const mobile = estate.form.mobility === 'mobile'
  const source = content.estate_forms.forms.find((f) => f.id === estate.form.id)
  const formName = (id: string) =>
    content.estate_forms.forms.find((f) => f.id === id)?.name ?? id
  const lost = `Your ${estate.form.name}, its larder and these upgrades will be lost: ${estate.installed_upgrades.map((u) => u.name).join(', ') || 'none'}.`
  return (
    <section>
      <p>
        {estate.form.mobility} · {estate.decay_stage} · Gauge: {estate.gauge}{' '}
        days
      </p>
      <p>
        {present ? 'Present at estate' : 'Away from estate; presence required'}{' '}
        ·{' '}
        <Link
          to={`/realm/map?destination=${encodeURIComponent(estate.realm_id)}`}
        >
          Travel to estate realm {estate.realm_id}
        </Link>
      </p>
      <h3>Transforms graph</h3>
      {content.estate_forms.forms.map((f) => (
        <p key={f.id}>
          {f.name} →{' '}
          {f.transforms_to
            .map(
              (id) =>
                content.estate_forms.forms.find((t) => t.id === id)?.name ?? id,
            )
            .join(', ') || 'No further forms'}
        </p>
      ))}
      <h3>Larder</h3>
      <p>
        Cover is shown per upkeep line; overlapping selectors share goods. Realm
        supplies and spoilage can change actual cover.
      </p>
      {Object.entries(estate.larder).map(([id, amount]) => (
        <p key={id}>
          {content.items.items.find((i) => i.id === id)?.name ?? id}:{' '}
          {amount / 1000}
        </p>
      ))}
      {(source?.upkeep ?? []).map((line, index) => {
        const stock = content.items.items
          .filter((item) => matches(item, line.selector))
          .reduce((sum, item) => sum + (estate.larder[item.id] ?? 0), 0)
        return (
          <p key={index}>
            {selectorLabel(line.selector)}: {coverDays(stock, line.per_day)} of
            cover
          </p>
        )
      })}
      {!source?.upkeep?.length && <p>No upkeep</p>}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          setConfirm({
            path: '/estates/me/larder',
            body: { item_id: itemId, quantity },
            message: `Deposit ${quantity} ${itemId}? Goods leave inventory permanently and cannot be withdrawn.`,
          })
        }}
      >
        <label>
          Larder item
          <select
            required
            value={itemId}
            onChange={(e) => setItemId(e.target.value)}
          >
            <option value="">Choose item</option>
            {inventory.data?.items
              .filter((h) =>
                content.items.items.some(
                  (i) =>
                    i.id === h.item_id &&
                    source?.upkeep?.some((line) => matches(i, line.selector)),
                ),
              )
              .map((h) => (
                <option key={h.item_id} value={h.item_id}>
                  {h.item_id} ({h.quantity} held)
                </option>
              ))}
          </select>
        </label>
        <label>
          Larder quantity
          <input
            type="number"
            required
            min="1"
            step="1"
            value={quantity}
            onChange={(e) => setQuantity(Number(e.target.value))}
          />
        </label>
        <button disabled={!present || action.isPending}>Deposit</button>
      </form>
      {mobile ? (
        <>
          <h3>Build fixed estate</h3>
          {content.estate_forms.forms
            .filter((f) => f.mobility === 'fixed' && f.tier === 1)
            .map((f) => (
              <article key={f.id}>
                <p>
                  {f.name} · {f.build_cost.gold} gold ·{' '}
                  {f.build_cost.goods
                    .map((l) => `${l.quantity} ${selectorLabel(l.selector)}`)
                    .join(', ')}{' '}
                  · Requires: {f.requires_realm_tags.join(', ') || 'none'}
                </p>
                <button
                  disabled={!present || action.isPending}
                  onClick={() =>
                    setConfirm({
                      path: '/estates/build',
                      body: { form_id: f.id },
                      message: `Build ${f.name}? Pay ${f.build_cost.gold} gold and consume ${f.build_cost.goods.map((l) => `${l.quantity} ${selectorLabel(l.selector)}`).join(', ') || 'no goods'}. ${lost}`,
                    })
                  }
                >
                  Build {f.name}
                </button>
              </article>
            ))}
          <h3>Buy fixed estate</h3>
          {estates.data
            ?.filter((e) => e.sale_price !== null)
            .map((e) => (
              <button
                key={e.id}
                disabled={!present || action.isPending}
                onClick={() =>
                  setConfirm({
                    path: `/estates/${encodeURIComponent(e.id)}/buy`,
                    body: {},
                    message: `Buy ${formName(e.form)} for current price ${e.sale_price} gold? Price is rechecked at purchase. ${lost}`,
                  })
                }
              >
                Buy {formName(e.form)} · {e.sale_price} gold
              </button>
            ))}
        </>
      ) : (
        <>
          <h3>Surrender estate</h3>
          {[false, true].map((donate) => (
            <button
              key={String(donate)}
              disabled={
                !present || action.isPending || estate.surrender_value == null
              }
              onClick={() =>
                setConfirm({
                  path: '/estates/me/surrender',
                  body: { donate },
                  message: `Give up ownership of ${estate.form.name}, its larder and upgrades (${estate.installed_upgrades.map((u) => u.name).join(', ') || 'none'}) to the realm and receive a basic mobile estate. ${donate ? 'Donation: no payout.' : `Up to ${estate.surrender_value} gold; the realm pays less if its treasury cannot cover it; rechecked on surrender.`}`,
                })
              }
            >
              {donate ? 'Donate estate' : 'Surrender for payout'}
            </button>
          ))}
        </>
      )}
      {estates.isError && <p role="alert">{estates.error.message}</p>}
      {confirm && (
        <div role="dialog" aria-modal="true" aria-label="Confirm estate action">
          <p>{confirm.message}</p>
          <button
            disabled={action.isPending}
            onClick={() =>
              action.mutate(confirm, { onSuccess: () => setConfirm(null) })
            }
          >
            Confirm estate action
          </button>
          <button disabled={action.isPending} onClick={() => setConfirm(null)}>
            Cancel
          </button>
        </div>
      )}
      {action.error && <p role="alert">{action.error.message}</p>}
    </section>
  )
}
