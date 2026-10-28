import { activeDefinition } from '../actions/activeDefinition'
import { useState } from 'react'
import type { CharacterProfile } from '../../api/characters'
import {
  type EquipmentSlot,
  type Item,
  type Trigger,
  useContent,
} from '../../api/content'
import { useActionState, useEquipmentChange } from '../../api/equipment'
import { useInventory } from '../../api/inventory'

const slots: EquipmentSlot[] = [
  'head',
  'chest',
  'gloves',
  'legs',
  'feet',
  'neck',
  'left_arm',
  'right_arm',
  'left_ring',
  'right_ring',
  'belt',
  'cape',
  'right_hand',
  'left_hand',
]

export function EquipmentPanel({ profile }: { profile: CharacterProfile }) {
  const content = useContent()
  const inventory = useInventory()
  const action = useActionState()
  const change = useEquipmentChange()
  if (content.status === 'error')
    return <p role="alert">Unable to load equipment content.</p>
  if (content.status !== 'ready') return <p>Loading equipment content…</p>
  if (inventory.isError) return <p role="alert">Unable to load inventory.</p>
  const items = content.content.items.items
  const equipment = profile.equipment ?? {}
  const fighting =
    activeDefinition(
      action.data?.active,
      content.content.skills.skills.flatMap((s) => s.actions),
    )?.resolver === 'combat'
  const disabled =
    fighting ||
    action.isError ||
    !action.data ||
    inventory.isPending ||
    change.isPending
  const held = items.filter((item) =>
    inventory.data?.items.some(
      (stack) => stack.item_id === item.id && stack.quantity > 0,
    ),
  )
  const twoHanded = items.find(
    (item) => item.id === equipment.right_hand?.item_id,
  )?.equip?.two_handed
  return (
    <section>
      <h2 className="text-3xl font-bold">Equipment</h2>
      {fighting && (
        <p>
          Equipment cannot change during combat. Stop combat to change
          equipment, belt or utility.
        </p>
      )}
      {!action.data && <p>Waiting for action status…</p>}
      {action.isError && <p role="alert">Unable to load action status.</p>}
      {change.error && <p role="alert">{change.error.message}</p>}
      <div
        className="mt-4 grid gap-4 md:grid-cols-3"
        aria-label="Equipment doll"
      >
        {slots.map((slot) => {
          const current = items.find(
            (item) => item.id === equipment[slot]?.item_id,
          )
          const blocked = slot === 'left_hand' && twoHanded
          const choices = held.filter(
            (item) =>
              item.equip &&
              (item.equip.slot === slot ||
                (item.equip.slot === 'ring' && slot.endsWith('_ring')) ||
                (item.equip.slot === 'arm' && slot.endsWith('_arm'))),
          )
          return (
            <article className="rounded border border-slate-700 p-3" key={slot}>
              <h3>{slot.replaceAll('_', ' ')}</h3>
              <p>{current?.name ?? 'Empty'}</p>
              {current && <Requirements item={current} profile={profile} />}
              {blocked && <p>Blocked by two-handed right-hand equipment</p>}
              {current && (
                <button
                  className="secondary-button mt-2"
                  disabled={disabled}
                  onClick={() =>
                    change.mutate({
                      path: '/equipment/unequip',
                      body: { slot },
                    })
                  }
                >
                  Unequip {slot.replaceAll('_', ' ')}
                </button>
              )}
              <fieldset disabled={disabled || !!blocked}>
                {choices.map((item) => (
                  <div key={item.id}>
                    <Requirements item={item} profile={profile} />
                    <button
                      className="secondary-button mt-2"
                      disabled={Object.entries(item.equip?.requires ?? {}).some(
                        ([id, level]) =>
                          (profile.skills.find((s) => s.id === id)?.level ??
                            0) < level,
                      )}
                      onClick={() =>
                        change.mutate({
                          path: '/equipment/equip',
                          body: { slot, item_id: item.id },
                        })
                      }
                    >
                      Equip {item.name} in {slot.replaceAll('_', ' ')}
                    </button>
                    {item.equip?.two_handed && (
                      <p>
                        Two-handed: returns left-hand equipment to inventory.
                      </p>
                    )}
                  </div>
                ))}
              </fieldset>
            </article>
          )
        })}
      </div>
      <ConsumablesPanel profile={profile} />
    </section>
  )
}

function Requirements({
  item,
  profile,
}: {
  item: Item
  profile: CharacterProfile
}) {
  return (
    <p>
      Requirements:{' '}
      {Object.entries(item.equip?.requires ?? {})
        .map(
          ([id, level]) =>
            `${profile.skills.find((s) => s.id === id)?.name ?? id} ${level}`,
        )
        .join(', ') || 'None'}
      {item.equip?.tool_class && ` · Tool: ${item.equip.tool_class}`}
    </p>
  )
}

type StackBody = {
  item_id: string | null
  quantity: number
  trigger?: Trigger | null
}
export function StackForm({
  items,
  current,
  belt = false,
  disabled,
  returnOnly = false,
  onSave,
}: {
  items: Item[]
  current?: { item_id: string; quantity: number; trigger?: Trigger }
  belt?: boolean
  disabled: boolean
  returnOnly?: boolean
  onSave: (body: StackBody) => void
}) {
  const [itemId, setItemId] = useState(current?.item_id ?? '')
  const [quantity, setQuantity] = useState(current?.quantity ?? 1)
  const [threshold, setThreshold] = useState(
    current?.trigger && 'hp_below_pct' in current.trigger
      ? current.trigger.hp_below_pct
      : 50,
  )
  const selected = items.find((i) => i.id === itemId)
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        if (disabled || returnOnly || !selected) return
        if (
          belt &&
          !selected.consumable?.buff &&
          (!Number.isFinite(threshold) || threshold <= 0 || threshold > 100)
        )
          return
        onSave({
          item_id: itemId,
          quantity,
          ...(belt
            ? {
                trigger: selected?.consumable?.buff
                  ? { buff_missing: true }
                  : { hp_below_pct: threshold },
              }
            : {}),
        })
      }}
    >
      <p>
        Assigned:{' '}
        {current
          ? `${items.find((i) => i.id === current.item_id)?.name ?? current.item_id} × ${current.quantity}`
          : 'Empty'}
      </p>
      <fieldset disabled={disabled || returnOnly}>
        <label className="mt-3 block">
          Item
          <select
            className="auth-input"
            required
            value={itemId}
            onChange={(e) => setItemId(e.target.value)}
          >
            <option value="">Choose item</option>
            {items.map((i) => (
              <option key={i.id} value={i.id}>
                {i.name}
              </option>
            ))}
          </select>
        </label>
        <label className="mt-3 block">
          Quantity
          <input
            className="auth-input"
            type="number"
            min={1}
            step={1}
            required
            value={quantity}
            onChange={(e) => setQuantity(Number(e.target.value))}
          />
        </label>
        {belt &&
          (selected?.consumable?.buff ? (
            <p>Trigger: reapply when buff missing</p>
          ) : (
            <label className="mt-3 block">
              HP below (%)
              <input
                className="auth-input"
                type="number"
                min={0}
                max={100}
                step="any"
                required
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
              />
            </label>
          ))}
        <button className="primary-button mt-3" disabled={!selected}>
          Assign stack
        </button>
      </fieldset>
      <button
        className="secondary-button mt-3"
        type="button"
        disabled={disabled || !current}
        onClick={() =>
          onSave({
            item_id: null,
            quantity: 0,
            ...(belt ? { trigger: null } : {}),
          })
        }
      >
        Return stack
      </button>
    </form>
  )
}

/** Shared combat preparation controls, also available beside the equipment doll. */
export function ConsumablesPanel({ profile }: { profile: CharacterProfile }) {
  const content = useContent()
  const inventory = useInventory()
  const action = useActionState()
  const change = useEquipmentChange()
  if (content.status === 'error' || inventory.isError)
    return <p role="alert">Unable to load consumable setup.</p>
  if (content.status !== 'ready' || inventory.isPending)
    return <p>Loading consumable setup…</p>
  const items = content.content.items.items
  const equipment = profile.equipment ?? {}
  const held = items.filter(
    (item) =>
      inventory.data?.items.some(
        (stack) => stack.item_id === item.id && stack.quantity > 0,
      ) ||
      equipment.utility?.item_id === item.id ||
      Object.values(profile.belt ?? {}).some(
        (stack) => stack.item_id === item.id,
      ),
  )
  const fighting =
    activeDefinition(
      action.data?.active,
      content.content.skills.skills.flatMap((s) => s.actions),
    )?.resolver === 'combat'
  const disabled =
    fighting || !action.data || action.isError || change.isPending
  const beltCapacity =
    profile.caps.belt_slots.effective +
    (items.find((item) => item.id === equipment.belt?.item_id)?.equip
      ?.belt_slots ?? 0)
  const positions = [
    ...new Set([
      ...Array.from({ length: beltCapacity }, (_, i) => i),
      ...Object.keys(profile.belt ?? {}).map(Number),
    ]),
  ].sort((a, b) => a - b)
  return (
    <section aria-label="Consumable setup">
      {fighting && <p>Belt and utility cannot change during combat.</p>}
      {action.isError && <p role="alert">Unable to load action status.</p>}
      {!action.data && <p>Waiting for action status…</p>}
      {change.error && <p role="alert">{change.error.message}</p>}
      <h3 className="mt-6">Combat utility</h3>
      <StackForm
        key={`utility-${JSON.stringify(equipment.utility)}`}
        items={held.filter((i) => i.consumable?.utility_for)}
        current={equipment.utility}
        disabled={disabled}
        onSave={(body) =>
          change.mutate({ path: '/equipment/utility', method: 'PUT', body })
        }
      />
      <h3 className="mt-6">Belt ({beltCapacity} positions)</h3>
      {positions.map((position) => (
        <div key={position}>
          <h4>
            Position {position + 1}
            {position >= beltCapacity ? ' (unavailable; return only)' : ''}
          </h4>
          <StackForm
            key={JSON.stringify(profile.belt?.[position])}
            items={held.filter((i) => i.consumable?.heal || i.consumable?.buff)}
            current={profile.belt?.[position]}
            belt
            disabled={disabled}
            returnOnly={position >= beltCapacity}
            onSave={(body) =>
              change.mutate({
                path: `/equipment/belt/${position}`,
                method: 'PUT',
                body,
              })
            }
          />
        </div>
      ))}
    </section>
  )
}
