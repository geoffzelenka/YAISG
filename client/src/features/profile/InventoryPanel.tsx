import { useInventory } from '../../api/inventory'
import { useContent } from '../../api/content'
import { useCharacterProfile } from '../../api/characters'

export function InventoryPanel() {
  const inventory = useInventory()
  const content = useContent()
  const profile = useCharacterProfile()
  if (inventory.isPending || profile.isPending || content.status === 'loading')
    return <p className="mt-8">Loading inventory…</p>
  if (inventory.isError || profile.isError || content.status === 'error')
    return <p className="mt-8 text-red-300">Unable to load inventory.</p>
  const names = new Map(
    content.content.items.items.map((item) => [item.id, item.name]),
  )
  const cap = profile.data?.caps.inventory_slots.effective ?? 0
  return (
    <section className="mt-10">
      <div className="flex items-end justify-between">
        <h3 className="text-2xl font-bold">Inventory</h3>
        <span className="text-slate-400">
          {inventory.data.items.length} / {cap} stacks
        </span>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {inventory.data.items.length === 0 ? (
          <p className="text-slate-500">Your inventory is empty.</p>
        ) : (
          inventory.data.items.map((stack) => (
            <article
              className="rounded-lg border border-slate-700 bg-slate-900 p-4"
              key={stack.item_id}
            >
              <strong>{names.get(stack.item_id) ?? stack.item_id}</strong>
              <p className="mt-1 text-2xl text-emerald-300">
                {stack.quantity.toLocaleString()}
              </p>
            </article>
          ))
        )}
      </div>
    </section>
  )
}
