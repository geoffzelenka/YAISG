import { useCallback, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import type { CharacterProfile } from '../../api/characters'
import { useContent } from '../../api/content'
import { useInventory } from '../../api/inventory'
import { useContribute, useRealm } from '../../api/realms'
import { Countdown } from './Countdown'
import { RelocationFlow } from './RelocationFlow'

function progressPercent(progress: number, target: number): number {
  if (target <= 0) return 100
  return Math.min(100, (progress / target) * 100)
}

export function ContributionForm({
  realmId,
  projectId,
  targets,
  totals,
}: {
  realmId: string
  projectId: string
  targets: { item_id: string; qty: number }[]
  totals: Record<string, number>
}) {
  const inventory = useInventory()
  const content = useContent()
  const contribute = useContribute(realmId, projectId)
  const held = useMemo(
    () =>
      new Map(
        inventory.data?.items.map((item) => [item.item_id, item.quantity]) ??
          [],
      ),
    [inventory.data],
  )
  const choices = targets.filter(
    (target) =>
      (held.get(target.item_id) ?? 0) > 0 &&
      target.qty - (totals[target.item_id] ?? 0) > 0,
  )
  const [selected, setSelected] = useState('')
  const target =
    choices.find((choice) => choice.item_id === selected) ?? choices[0]
  const maximum = target
    ? Math.min(
        held.get(target.item_id) ?? 0,
        target.qty - (totals[target.item_id] ?? 0),
      )
    : 0
  const [quantity, setQuantity] = useState(1)
  if (inventory.isPending || content.status === 'loading')
    return <p>Loading contribution options…</p>
  if (inventory.isError || content.status === 'error')
    return <p className="text-red-300">Unable to load contribution options.</p>
  const itemNames = new Map(
    content.content.items.items.map((item) => [item.id, item.name]),
  )
  if (!target)
    return (
      <p className="text-slate-500">
        You hold none of the remaining target items.
      </p>
    )
  const clamped = Math.max(1, Math.min(quantity, maximum))
  return (
    <form
      className="mt-4 flex flex-wrap items-end gap-3"
      onSubmit={(event) => {
        event.preventDefault()
        contribute.mutate({ item_id: target.item_id, quantity: clamped })
      }}
    >
      <label>
        Item
        <select
          className="auth-input"
          value={target.item_id}
          onChange={(event) => {
            setSelected(event.target.value)
            setQuantity(1)
          }}
        >
          {choices.map((choice) => (
            <option key={choice.item_id} value={choice.item_id}>
              {itemNames.get(choice.item_id) ?? choice.item_id}
            </option>
          ))}
        </select>
      </label>
      <label>
        Quantity
        <input
          aria-label="Quantity"
          className="auth-input w-28"
          min={1}
          max={maximum}
          type="number"
          value={clamped}
          onChange={(event) =>
            setQuantity(
              Math.max(1, Math.min(Number(event.target.value) || 1, maximum)),
            )
          }
        />
      </label>
      <button className="primary-button" disabled={contribute.isPending}>
        Contribute
      </button>
      {contribute.error && (
        <p className="w-full text-red-300" role="alert">
          {contribute.error.message}
        </p>
      )}
    </form>
  )
}

export function TransitionBanner({
  realmId,
  toNodeId,
  completesAt,
}: {
  realmId: string
  toNodeId: string
  completesAt: string
}) {
  const client = useQueryClient()
  const content = useContent()
  const target =
    content.status === 'ready'
      ? content.content.development.nodes.find((node) => node.id === toNodeId)
      : undefined
  const expire = useCallback(() => {
    void client.invalidateQueries({ queryKey: ['realms', realmId] })
    void client.invalidateQueries({
      queryKey: ['characters', 'me', 'actions', 'available'],
    })
  }, [client, realmId])
  return (
    <aside
      className="mb-6 rounded-xl border border-amber-400 bg-amber-950/40 p-5"
      role="status"
    >
      <strong>Realm transition underway: {target?.name ?? toNodeId}</strong>
      <p className="mt-1">
        New identity arrives in{' '}
        <Countdown completesAt={completesAt} onExpire={expire} />
      </p>
    </aside>
  )
}

export function RealmPanel({ profile }: { profile: CharacterProfile }) {
  const realm = useRealm(profile.character.current_realm_id)
  const content = useContent()
  if (realm.isPending || content.status === 'loading')
    return <p>Loading realm…</p>
  if (realm.isError || content.status === 'error')
    return <p className="text-red-300">Unable to load realm.</p>
  const nodeDefinition = content.content.development.nodes.find(
    (node) => node.id === realm.data.node.id,
  )
  return (
    <section>
      {realm.data.pending_transition && (
        <TransitionBanner
          realmId={realm.data.id}
          toNodeId={realm.data.pending_transition.to_node_id}
          completesAt={realm.data.pending_transition.completes_at}
        />
      )}
      <h2 className="text-3xl font-bold">{realm.data.name}</h2>
      <p className="mt-2 text-slate-400">
        {realm.data.node.name} ·{' '}
        {nodeDefinition?.archetype ?? 'unknown archetype'} ·{' '}
        {realm.data.node.tags.join(', ')}
      </p>
      <h3 className="mt-8 text-xl font-semibold">Projects</h3>
      <div className="mt-3 space-y-4">
        {realm.data.active_projects.map((project) => (
          <article
            className="rounded-xl border border-slate-700 bg-slate-900 p-5"
            key={project.project_id}
          >
            <h4 className="font-semibold">{project.name}</h4>
            {project.targets.map((target) => {
              const progress = project.contribution_totals[target.item_id] ?? 0
              return (
                <div className="mt-3" key={target.item_id}>
                  <div className="flex justify-between text-sm">
                    <span>{target.item_id}</span>
                    <span>
                      {progress} / {target.qty}
                    </span>
                  </div>
                  <div className="mt-1 h-2 overflow-hidden rounded bg-slate-700">
                    <div
                      className="h-full bg-emerald-400"
                      style={{
                        width: `${progressPercent(progress, target.qty)}%`,
                      }}
                    />
                  </div>
                </div>
              )
            })}
            <ContributionForm
              realmId={realm.data.id}
              projectId={project.project_id}
              targets={project.targets}
              totals={project.contribution_totals}
            />
          </article>
        ))}
        {realm.data.active_projects.length === 0 && (
          <p className="text-slate-500">No active projects.</p>
        )}
      </div>
      <h3 className="mt-8 text-xl font-semibold">Path forward</h3>
      {realm.data.outgoing_edges.map((edge) => (
        <div className="mt-3" key={edge.edge_id}>
          <div className="flex justify-between">
            <span>{edge.edge_id}</span>
            <span>
              {edge.progress} / {edge.target}
            </span>
          </div>
          <div className="mt-1 h-3 overflow-hidden rounded bg-slate-700">
            <div
              className="h-full bg-sky-400"
              style={{
                width: `${progressPercent(edge.progress, edge.target)}%`,
              }}
            />
          </div>
        </div>
      ))}
      <RelocationFlow currentRealmId={profile.character.current_realm_id} />
    </section>
  )
}
