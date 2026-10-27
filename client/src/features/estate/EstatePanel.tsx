import { useMemo, useState } from 'react'

import { useContent } from '../../api/content'
import {
  canAfford,
  EstateApiError,
  useEstate,
  usePurchaseUpgrade,
  useTransformEstate,
} from '../../api/estates'
import { useInventory } from '../../api/inventory'

function Cost({ cost }: { cost: { item_id: string; qty: number }[] }) {
  const content = useContent()
  if (content.status !== 'ready') return null
  const names = new Map(
    content.content.items.items.map((item) => [item.id, item.name]),
  )
  return (
    <>
      {cost
        .map(
          (entry) =>
            `${entry.qty} ${names.get(entry.item_id) ?? entry.item_id}`,
        )
        .join(', ')}
    </>
  )
}

function errorMessage(error: Error | null): string | null {
  if (error === null) return null
  if (error instanceof EstateApiError) return `${error.message} (${error.code})`
  return error.message
}

export function EstatePanel() {
  const estate = useEstate()
  const inventory = useInventory()
  const content = useContent()
  const purchase = usePurchaseUpgrade()
  const transform = useTransformEstate()
  const [confirmForm, setConfirmForm] = useState<string | null>(null)
  const held = useMemo(
    () =>
      new Map(
        inventory.data?.items.map((item) => [item.item_id, item.quantity]) ??
          [],
      ),
    [inventory.data],
  )
  if (estate.isPending || inventory.isPending || content.status === 'loading')
    return <p>Loading estate…</p>
  if (estate.isError || inventory.isError || content.status === 'error')
    return <p className="text-red-300">Unable to load estate.</p>

  const installedIds = new Set(
    estate.data.installed_upgrades.map((upgrade) => upgrade.upgrade_id),
  )
  const freeSlots =
    estate.data.upgrade_slots - estate.data.installed_upgrades.length
  const source = content.content.estate_forms.forms.find(
    (form) => form.id === estate.data.form.id,
  )
  const transformations = content.content.estate_forms.forms.filter((form) =>
    source?.transforms_to.includes(form.id),
  )
  const destination = transformations.find((form) => form.id === confirmForm)
  const slotDelta =
    (destination?.upgrade_slots ?? 0) - estate.data.form.upgrade_slots

  return (
    <section>
      <h2 className="text-3xl font-bold">{estate.data.form.name}</h2>
      <p className="mt-2 text-slate-400">
        Tier {estate.data.tier} ·{' '}
        {estate.data.form.tags.length
          ? estate.data.form.tags.join(', ')
          : 'No tags'}
      </p>
      <h3 className="mt-8 text-xl font-semibold">Upgrade slots</h3>
      <div className="mt-3 grid max-w-2xl grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: estate.data.upgrade_slots }, (_, slot) => {
          const installed = estate.data.installed_upgrades.find(
            (upgrade) => upgrade.slot_index === slot,
          )
          return (
            <article
              className="min-h-24 rounded-lg border border-slate-700 bg-slate-900 p-3"
              data-testid={`estate-slot-${slot}`}
              key={slot}
            >
              {installed ? (
                <>
                  <strong>{installed.name}</strong>
                  <p
                    className={
                      installed.status === 'active'
                        ? 'mt-2 text-sm text-emerald-300'
                        : 'mt-2 text-sm text-amber-300'
                    }
                    title={installed.inert_reason ?? undefined}
                  >
                    {installed.status}
                  </p>
                </>
              ) : (
                <span className="text-slate-500">Empty</span>
              )}
            </article>
          )
        })}
      </div>
      <h3 className="mt-8 text-xl font-semibold">Available upgrades</h3>
      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        {content.content.upgrades.upgrades
          .filter((upgrade) => !installedIds.has(upgrade.id))
          .map((upgrade) => {
            const affordable = canAfford(upgrade.cost, held) && freeSlots > 0
            return (
              <article
                className="rounded-lg border border-slate-700 bg-slate-900 p-4"
                key={upgrade.id}
              >
                <strong>{upgrade.name}</strong>
                <p className="mt-2 text-sm text-slate-400">
                  <Cost cost={upgrade.cost} />
                </p>
                <button
                  className="primary-button mt-3"
                  disabled={!affordable || purchase.isPending}
                  onClick={() => purchase.mutate(upgrade.id)}
                >
                  {affordable
                    ? 'Purchase'
                    : freeSlots <= 0
                      ? 'No free slot'
                      : 'Cannot afford'}
                </button>
              </article>
            )
          })}
      </div>
      <h3 className="mt-8 text-xl font-semibold">Transform estate</h3>
      <div className="mt-3 flex flex-wrap gap-3">
        {transformations.map((form) => (
          <button
            className="secondary-button"
            key={form.id}
            onClick={() => setConfirmForm(form.id)}
          >
            Transform to {form.name}
          </button>
        ))}
        {transformations.length === 0 && (
          <p className="text-slate-500">No transformations available.</p>
        )}
      </div>
      {confirmForm && destination && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-slate-950/80 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="transform-title"
        >
          <div className="max-w-md rounded-xl border border-slate-600 bg-slate-900 p-6">
            <h3 className="text-xl font-bold" id="transform-title">
              Transform to {destination.name}?
            </h3>
            <p className="mt-3 text-slate-300">
              Upgrade slots change by {slotDelta >= 0 ? '+' : ''}
              {slotDelta}. Form caps and modifiers will be replaced by{' '}
              {destination.name}'s values.
            </p>
            <p className="mt-2 text-slate-400">
              Cost: {destination.build_cost.gold} gold,{' '}
              {destination.build_cost.goods
                .map(
                  (line) =>
                    `${line.quantity} ${'item' in line.selector ? line.selector.item : line.selector.class}`,
                )
                .join(', ')}
            </p>
            <div className="mt-5 flex gap-3">
              <button
                className="primary-button"
                disabled={transform.isPending}
                onClick={() =>
                  transform.mutate(confirmForm, {
                    onSuccess: () => setConfirmForm(null),
                  })
                }
              >
                Confirm transformation
              </button>
              <button
                className="secondary-button"
                onClick={() => setConfirmForm(null)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
      {(purchase.error || transform.error) && (
        <p className="mt-4 text-red-300" role="alert">
          {errorMessage(purchase.error ?? transform.error)}
        </p>
      )}
    </section>
  )
}
