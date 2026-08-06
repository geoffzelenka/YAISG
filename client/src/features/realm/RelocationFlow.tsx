import { useState } from 'react'

import { useContent } from '../../api/content'
import {
  RealmApiError,
  useRelocate,
  useRelocationPreview,
} from '../../api/realms'

function errorMessage(error: Error | null): string | null {
  if (error === null) return null
  if (error instanceof RealmApiError) return `${error.message} (${error.code})`
  return error.message
}

export function RelocationFlow({
  currentRealmId,
  initialDestination = null,
}: {
  currentRealmId: string
  initialDestination?: string | null
}) {
  const content = useContent()
  const [destination, setDestination] = useState<string | null>(
    initialDestination,
  )
  const preview = useRelocationPreview(destination)
  const relocate = useRelocate()
  if (content.status !== 'ready') return null
  const realms = content.content.realms.realms.filter(
    (realm) => realm.id !== currentRealmId,
  )
  return (
    <section className="mt-8 rounded-xl border border-slate-700 bg-slate-900 p-5">
      <h3 className="text-xl font-semibold">Relocate estate</h3>
      <label className="mt-4 block">
        Destination
        <select
          className="auth-input"
          value={destination ?? ''}
          onChange={(event) => setDestination(event.target.value || null)}
        >
          <option value="">Choose a realm</option>
          {realms.map((realm) => (
            <option key={realm.id} value={realm.id}>
              {realm.name}
            </option>
          ))}
        </select>
      </label>
      {preview.isPending && destination && (
        <p className="mt-3">Computing route…</p>
      )}
      {preview.data && (
        <div className="mt-4">
          <p>
            Cost: {preview.data.cost.gold} gold
            {preview.data.cost.items.map(
              (item) => `, ${item.qty} ${item.item_id}`,
            )}
          </p>
          <p>
            Travel time: {Math.ceil(preview.data.cost.time_ms / 1000)} seconds
          </p>
          <button
            className="primary-button mt-3"
            disabled={relocate.isPending}
            onClick={() => relocate.mutate(preview.data.destination_realm_id)}
          >
            Confirm relocation
          </button>
        </div>
      )}
      {(preview.error || relocate.error) && (
        <p className="mt-3 text-red-300" role="alert">
          {errorMessage(preview.error ?? relocate.error)}
        </p>
      )}
    </section>
  )
}
