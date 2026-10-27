import { useState } from 'react'
import type { CharacterProfile } from '../../api/characters'
import { useContent } from '../../api/content'
import { useEstate } from '../../api/estates'
import type { RealmMap } from '../../api/realms'
import {
  useStartTravel,
  useTravelPreview,
  type TravelRequest,
} from '../../api/travel'

export function TravelForm({
  profile,
  nodes,
}: {
  profile: CharacterProfile
  nodes: RealmMap['nodes']
}) {
  const estate = useEstate()
  const content = useContent()
  const preview = useTravelPreview()
  const start = useStartTravel()
  const [destination, setDestination] = useState('')
  const [mode, setMode] = useState<TravelRequest['mode']>('visit')
  const canRelocate =
    estate.data?.form.mobility === 'mobile' &&
    estate.data.realm_id === profile.character.current_realm_id
  const effectiveMode = canRelocate ? mode : 'visit'
  const input = { destination_realm_id: destination, mode: effectiveMode }
  const currentPreview =
    preview.variables?.destination_realm_id === destination &&
    preview.variables.mode === effectiveMode
      ? preview.data
      : undefined
  const busy = preview.isPending || start.isPending
  const itemName = (id: string) =>
    content.status === 'ready'
      ? (content.content.items.items.find((item) => item.id === id)?.name ?? id)
      : id
  return (
    <form
      className="mt-6 space-y-3"
      onSubmit={(event) => {
        event.preventDefault()
        start.reset()
        preview.mutate(input)
      }}
    >
      <label className="block">
        Destination
        <select
          className="auth-input"
          value={destination}
          disabled={busy}
          required
          onChange={(event) => {
            setDestination(event.target.value)
            preview.reset()
            start.reset()
          }}
        >
          <option value="">Choose a realm</option>
          {nodes
            .filter(
              (node) => node.realm_id !== profile.character.current_realm_id,
            )
            .map((node) => (
              <option key={node.realm_id} value={node.realm_id}>
                {node.name}
              </option>
            ))}
        </select>
      </label>
      <label className="block">
        Mode
        <select
          className="auth-input"
          value={effectiveMode}
          disabled={busy}
          onChange={(event) => {
            setMode(event.target.value as TravelRequest['mode'])
            preview.reset()
            start.reset()
          }}
        >
          <option value="visit">Visit</option>
          <option value="relocate" disabled={!canRelocate}>
            Relocate
          </option>
        </select>
      </label>
      {!canRelocate && (
        <p>Relocate requires a mobile estate in your current realm.</p>
      )}
      <button className="secondary-button" disabled={!destination || busy}>
        Preview journey
      </button>
      {currentPreview && (
        <div>
          <p>
            Estimated route; costs are checked by the server when each edge
            starts.
          </p>
          <ol>
            {currentPreview.route.map((step) => (
              <li key={step.edge_id}>
                {step.edge_id} →{' '}
                {nodes.find(
                  (node) => node.realm_id === step.destination_realm_id,
                )?.name ?? step.destination_realm_id}
                : {(step.time_ms / 1000).toFixed(2)}s · Supplies:{' '}
                {step.supplies
                  .map(
                    (supply) =>
                      `${supply.quantity}× ${supply.selector.item ? itemName(supply.selector.item) : `${supply.selector.class}${supply.selector.tier ? ` (tier ${supply.selector.tier})` : ''}`}`,
                  )
                  .join(', ') || 'None'}
              </li>
            ))}
          </ol>
          <button
            type="button"
            className="primary-button"
            disabled={busy || !currentPreview.route.length}
            onClick={() =>
              start.mutate(input, { onSuccess: () => preview.reset() })
            }
          >
            Start journey
          </button>
        </div>
      )}
      {(preview.error || start.error) && (
        <p role="alert">{(preview.error ?? start.error)?.message}</p>
      )}
    </form>
  )
}
