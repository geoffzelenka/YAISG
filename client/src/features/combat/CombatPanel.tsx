import { useState } from 'react'
import { ConsumablesPanel } from '../equipment/EquipmentPanel'
import { useAvailableActions, useStartAction } from '../../api/actions'
import type { CharacterProfile } from '../../api/characters'
import { useContent } from '../../api/content'
import { useActionState, useEquipmentChange } from '../../api/equipment'
import { ResolverDetails } from '../actions/ResolverDetails'
import { isRecord } from '../actions/journey'
import { resolverResolutions } from '../actions/resolverPresentation'

export function CombatPanel({ profile }: { profile: CharacterProfile }) {
  const content = useContent()
  const available = useAvailableActions()
  const start = useStartAction()
  const stance = useEquipmentChange()
  const feed = useActionState()
  const [location, setLocation] = useState('')
  const [actionId, setActionId] = useState('')
  if (content.status === 'error')
    return <p role="alert">Unable to load combat content.</p>
  if (content.status !== 'ready') return <p>Loading combat content…</p>
  const actions = content.content.skills.skills
    .flatMap((s) => s.actions)
    .filter((a) => a.resolver === 'combat')
  const offered = available.data?.skills.flatMap((s) => s.actions) ?? []
  const encounters = actions.filter((a) =>
    offered.some((o) => o.action_id === a.id),
  )
  const locations = [...new Set(encounters.map((a) => a.location ?? ''))]
  const selectedLocation = locations.includes(location)
    ? location
    : locations[0]
  const choices = encounters.filter((a) => a.location === selectedLocation)
  const selected = choices.find((a) => a.id === actionId) ?? choices[0]
  const status = offered.find((a) => a.action_id === selected?.id)
  const active = feed.data?.active
  const encounter = actions.find((a) => a.id === active?.action_id)
  return (
    <section>
      <h2 className="text-3xl font-bold">Combat</h2>
      <p>
        HP: {profile.hp ?? 'Unknown'} / {profile.max_hp ?? 'Unknown'}
      </p>
      {profile.hp !== undefined && profile.max_hp !== undefined && (
        <progress
          aria-label="Hit points"
          value={profile.hp}
          max={profile.max_hp}
        />
      )}
      <label className="mt-3 block">
        Stance
        <select
          className="auth-input"
          value={profile.character.stance ?? ''}
          disabled={stance.isPending}
          onChange={(e) =>
            stance.mutate({
              path: '/characters/me/stance',
              method: 'PUT',
              body: { stance: e.target.value },
            })
          }
        >
          {Object.entries(content.content.progression.stances ?? {}).map(
            ([id, split]) => (
              <option key={id} value={id}>
                {id} (Style {split.style * 100}%, Accuracy{' '}
                {split.accuracy * 100}%)
              </option>
            ),
          )}
        </select>
      </label>
      {stance.error && <p role="alert">{stance.error.message}</p>}
      {available.isPending && <p>Loading encounters…</p>}
      {available.isError && <p role="alert">Unable to load encounters.</p>}
      {!available.isPending && !available.isError && !encounters.length && (
        <p>No combat encounters offered here.</p>
      )}
      <label className="mt-3 block">
        Location
        <select
          className="auth-input"
          value={selectedLocation ?? ''}
          onChange={(e) => setLocation(e.target.value)}
        >
          {locations.map((l) => (
            <option key={l}>{l}</option>
          ))}
        </select>
      </label>
      <label className="mt-3 block">
        Combatant
        <select
          className="auth-input"
          value={selected?.id ?? ''}
          onChange={(e) => setActionId(e.target.value)}
        >
          {choices.map((a) => (
            <option key={a.id} value={a.id}>
              {content.content.combatants.combatants.find(
                (c) => c.id === a.combatant_id,
              )?.name ?? a.name}
            </option>
          ))}
        </select>
      </label>
      {status && (
        <p>
          Cycle: {status.cycle_ms} ms ·{' '}
          {status.blocked_by.join(', ') || 'Ready'}
        </p>
      )}
      <button
        className="primary-button"
        disabled={
          !status?.startable ||
          start.isPending ||
          active?.action_id === selected?.id
        }
        onClick={() => selected && start.mutate(selected.id)}
      >
        Start combat
      </button>
      {start.error && <p role="alert">{start.error.message}</p>}
      {active && encounter && (
        <div>
          <h3>
            Current encounter:{' '}
            {content.content.combatants.combatants.find(
              (c) => c.id === encounter.combatant_id,
            )?.name ?? encounter.name}{' '}
            at {encounter.location}
          </h3>
          <p>Cycle: {active.cycle_ms} ms</p>
          <dl>
            {['opponent_hp', 'offense', 'defense', 'respawn_remaining_ms'].map(
              (key) => (
                <div key={key}>
                  <dt>{key.replaceAll('_', ' ')}</dt>
                  <dd>{encounterValue(active.meta?.[key])}</dd>
                </div>
              ),
            )}
          </dl>
        </div>
      )}
      <ConsumablesPanel profile={profile} />
      <h3 className="mt-6">Encounter log</h3>
      <EncounterLog
        details={feed.data?.since_last.details}
        reason={feed.data?.stop_reason ?? feed.data?.since_last.stop_reason}
      />
    </section>
  )
}

function EncounterLog({
  details,
  reason,
}: {
  details?: Record<string, unknown>
  reason?: string | null
}) {
  const [entries, setEntries] = useState<
    { details?: Record<string, unknown>; reason?: string | null }[]
  >([{ details, reason }])
  const [previous, setPrevious] = useState({ details, reason })
  if (details !== previous.details || reason !== previous.reason) {
    setPrevious({ details, reason })
    if (
      reason ||
      resolverResolutions(details).some(
        (value) => isRecord(value) && typeof value.kills === 'number',
      )
    )
      setEntries([...entries, { details, reason }].slice(-30))
  }
  const rows = entries.length ? entries : [{ details, reason }]
  return (
    <div aria-live="polite">
      {rows.map((entry, index) => (
        <div key={index}>
          <ResolverDetails details={entry.details} />
          {entry.reason && <p>Stopped: {entry.reason}</p>}
        </div>
      ))}
    </div>
  )
}

/** Pools are serialized exact fractions; present the server value as a number. */
function encounterValue(value: unknown): string {
  if (typeof value === 'number') return String(value)
  if (
    Array.isArray(value) &&
    value.length === 2 &&
    typeof value[0] === 'number' &&
    typeof value[1] === 'number' &&
    value[1] !== 0
  )
    return (value[0] / value[1]).toLocaleString()
  return 'Unknown'
}
