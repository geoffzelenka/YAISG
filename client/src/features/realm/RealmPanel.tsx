import { useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import type { CharacterProfile } from '../../api/characters'
import { useContent } from '../../api/content'
import { useRealm } from '../../api/realms'
import { DevelopmentControls } from './DevelopmentControls'
import { selectorLabel } from './presentation'
import { Countdown } from './Countdown'

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
  const [selectedRealm, setSelectedRealm] = useState('')
  const realm = useRealm(selectedRealm || profile.character.current_realm_id)
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
          toNodeId={realm.data.pending_transition.to_node}
          completesAt={realm.data.pending_transition.completes_at}
        />
      )}
      <label>
        Inspect realm
        <select
          value={selectedRealm || profile.character.current_realm_id}
          onChange={(e) => setSelectedRealm(e.target.value)}
        >
          {content.content.realms.realms
            .filter((r) => !r.isolated)
            .map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
        </select>
      </label>
      <h2 className="text-3xl font-bold">{realm.data.name}</h2>
      <p className="mt-2 text-slate-400">
        {realm.data.node.name} · Tier {realm.data.node.tier} ·{' '}
        {nodeDefinition?.realm_type ?? 'unknown type'} ·{' '}
        {realm.data.node.tags.join(', ')}
      </p>
      <p>
        {realm.data.decay_stage} · Gauge: {realm.data.gauge} days
      </p>
      <h3>Short lines</h3>
      {realm.data.lines
        .filter((line) => line.below_reserve)
        .map((line) => (
          <p key={line.line_key}>
            {selectorLabel(line.selector)}
            {line.value_measured ? ' (reference value)' : ''} · stock{' '}
            {line.stock / 1000}, reserve {line.reserve / 1000} · in transit{' '}
            {line.in_transit / 1000}
          </p>
        ))}
      <DevelopmentControls
        realm={realm.data}
        profile={profile}
        content={content.content}
      />
    </section>
  )
}
