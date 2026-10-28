import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import type { CharacterProfile } from '../../api/characters'
import type { Content } from '../../api/content'
import { useEstate } from '../../api/estates'
import { useInventory } from '../../api/inventory'
import {
  type Credits,
  type RealmEstate,
  type Vote,
  useDevelopmentRead,
  useDevelopmentAction,
} from '../../api/development'
import type { RealmDetail } from '../../api/realms'
import { Countdown } from './Countdown'
import { kickoffReason } from './kickoffReason'
import { matches, selectorLabel } from './presentation'

function TagCredit({ realmId, tagId }: { realmId: string; tagId: string }) {
  const credits = useDevelopmentRead<Credits>(
    realmId,
    `tags/${encodeURIComponent(tagId)}`,
  )
  return (
    <details>
      <summary>{tagId} credits</summary>
      {credits.isError ? (
        <p role="alert">{credits.error.message}</p>
      ) : !credits.data ? (
        <p>Loading credits…</p>
      ) : (
        <>
          <p>Kickoff: {credits.data.kicked_off_by ?? 'Inherent / no player'}</p>
          {Object.entries(credits.data.contributions).map(([id, amount]) => (
            <p key={id}>
              {id}: {amount}
            </p>
          ))}
          <p>Realm share: {credits.data.realm_share}</p>
        </>
      )}
    </details>
  )
}
export function VotePanel({
  vote,
  characterId,
  onCast,
  onExpire,
  pending,
}: {
  vote: Vote
  characterId: string
  onCast: (choice: 'yes' | 'no') => void
  onExpire: () => void
  pending: boolean
}) {
  const eligible = vote.participation.find(
    (p) => p.character_id === characterId,
  )
  return (
    <section>
      <h3>
        Vote: {vote.upgrade_id} · {vote.status}
      </h3>
      {vote.status === 'open' ? (
        <p>
          Closes in{' '}
          <Countdown completesAt={vote.closes_at} onExpire={onExpire} />
        </p>
      ) : (
        <p>
          Yes weight: {vote.yes_weight}; No weight: {vote.no_weight}
        </p>
      )}
      <ul>
        {vote.participation.map((p) => (
          <li key={p.character_id}>
            {p.character_id} · weight {p.weight} ·{' '}
            {p.voted_at ? 'Voted' : 'Not voted'}
          </li>
        ))}
      </ul>
      {vote.status === 'open' && (
        <>
          <p>
            {!eligible
              ? 'You are not eligible for this ballot'
              : eligible.voted_at
                ? 'Your vote is recorded'
                : 'You may vote from anywhere'}
          </p>
          {(['yes', 'no'] as const).map((choice) => (
            <button
              key={choice}
              disabled={pending || !eligible || !!eligible.voted_at}
              onClick={() => onCast(choice)}
            >
              Vote {choice}
            </button>
          ))}
        </>
      )}
    </section>
  )
}
export function DevelopmentControls({
  realm,
  profile,
  content,
}: {
  realm: RealmDetail
  profile: CharacterProfile
  content: Content
}) {
  const client = useQueryClient()
  const availability = useDevelopmentRead<
    Record<string, { code: string; message: string } | null>
  >(realm.id, 'projects/availability')
  const estate = useEstate()
  const inventory = useInventory()
  const vote = useDevelopmentRead<Vote | null>(realm.id, 'vote')
  const estates = useDevelopmentRead<RealmEstate[]>(realm.id, 'estates')
  const action = useDevelopmentAction()
  const [confirmation, setConfirmation] = useState<{
    path: string
    body: unknown
    message: string
  } | null>(null)
  const [itemId, setItemId] = useState('')
  const [quantity, setQuantity] = useState(1)
  const node = content.development.nodes.find((n) => n.id === realm.node.id)
  const tags = new Set([...realm.node.tags, ...realm.tags.map((t) => t.tag_id)])
  const present = profile.character.current_realm_id === realm.id
  const resident = estate.data?.realm_id === realm.id
  const path = `/realms/${encodeURIComponent(realm.id)}`
  const run = realm.active_run
  const ask = (suffix: string, body: unknown, message: string) =>
    setConfirmation({ path: path + suffix, body, message })
  return (
    <>
      <p>
        {present
          ? 'You are present in this realm'
          : 'Presence required to contribute or kick off'}{' '}
        ·{' '}
        <Link to={`/realm/map?destination=${encodeURIComponent(realm.id)}`}>
          Travel
        </Link>
      </p>
      <h3>Tags</h3>
      {realm.node.tags.map((t) => (
        <p key={t}>{t} · inherent</p>
      ))}
      {realm.tags.map((t) => (
        <TagCredit key={t.tag_id} realmId={realm.id} tagId={t.tag_id} />
      ))}
      <h3>Projects</h3>
      {availability.isError && <p role="alert">{availability.error.message}</p>}
      {run && (
        <article>
          <h4>
            {content.projects.projects.find((p) => p.id === run.project_id)
              ?.name ?? run.project_id}{' '}
            · {run.status} {run.stalled && '· Stalled'}
          </h4>
          {run.required.map((line, i) => (
            <p key={i}>
              {selectorLabel(line.selector)}: {run.contributed[i]} /{' '}
              {line.quantity}
            </p>
          ))}
          {run.build_completes_at && (
            <Countdown
              completesAt={run.build_completes_at}
              onExpire={() => {
                void client.invalidateQueries({
                  queryKey: ['realms', realm.id],
                })
              }}
            />
          )}
          {run.status === 'funding' && (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                ask(
                  '/project/contribute',
                  { item_id: itemId, quantity },
                  `Contribute up to ${quantity} ${itemId}. Consumed goods cannot be recovered.`,
                )
              }}
            >
              <label>
                Contribution item
                <select
                  required
                  value={itemId}
                  onChange={(e) => setItemId(e.target.value)}
                >
                  <option value="">Choose item</option>
                  {inventory.data?.items
                    .filter((holding) =>
                      content.items.items.some(
                        (item) =>
                          item.id === holding.item_id &&
                          run.required.some((line) =>
                            matches(item, line.selector),
                          ),
                      ),
                    )
                    .map((item) => (
                      <option key={item.item_id} value={item.item_id}>
                        {item.item_id} ({item.quantity} held)
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Quantity
                <input
                  type="number"
                  min="1"
                  step="1"
                  required
                  value={quantity}
                  onChange={(e) => setQuantity(Number(e.target.value))}
                />
              </label>
              <button disabled={!present || action.isPending}>
                Contribute
              </button>
            </form>
          )}
        </article>
      )}
      {node?.projects.map((id) => {
        const project = content.projects.projects.find((p) => p.id === id)
        if (!project) return null
        const serverReason = availability.data?.[id]
        const reason = serverReason
          ? `${serverReason.message} (${serverReason.code})`
          : !present
            ? 'Presence required'
            : kickoffReason(
                project,
                realm,
                resident,
                vote.data?.status === 'open',
              )
        return (
          <article key={id}>
            <h4>{project.name}</h4>
            <p>
              Kickoff: {project.kickoff.gold} gold;{' '}
              {project.kickoff.goods
                .map((l) => `${l.quantity} ${selectorLabel(l.selector)}`)
                .join(', ') || 'no goods'}
              . Who: {project.kickoff.who}
            </p>
            <p>
              {project.cost.length
                ? 'Funding: '
                : 'Fully paid at kickoff; no contributions required.'}{' '}
              {project.cost
                .map((l) => `${l.quantity} ${selectorLabel(l.selector)}`)
                .join(', ')}{' '}
              · Build: {project.build_seconds} seconds
            </p>
            <p>{reason ?? 'Available; server rechecks on confirmation'}</p>
            <button
              disabled={
                !!reason ||
                action.isPending ||
                !vote.isSuccess ||
                !estate.isSuccess ||
                !availability.isSuccess
              }
              onClick={() =>
                ask(
                  `/projects/${encodeURIComponent(id)}/kickoff`,
                  {},
                  `Kick off ${project.name}? Pay ${project.kickoff.gold} gold and consume ${project.kickoff.goods.map((l) => `${l.quantity} ${selectorLabel(l.selector)}`).join(', ') || 'no goods'}; kickoff payment is not refunded.`,
                )
              }
            >
              Kick off {project.name}
            </button>
          </article>
        )
      })}
      <h3>Upgrades</h3>
      {node?.upgrades.map((upgrade) => {
        const missing = upgrade.required_tags.some((t) => !tags.has(t))
        const short = realm.lines.some(
          (l) => l.stock < l.draw_per_day * content.economy.vote.min_stock_days,
        )
        return (
          <article key={upgrade.id}>
            <h4>
              {content.development.nodes.find((n) => n.id === upgrade.to_node)
                ?.name ?? upgrade.to_node}
            </h4>
            <p>
              {upgrade.required_tags
                .map((t) => `${t}: ${tags.has(t) ? 'held' : 'missing'}`)
                .join(', ') || 'No tags required'}
            </p>
            <p>
              Fee: {upgrade.fee_gold} gold (not refunded). Residents may call
              from anywhere.
            </p>
            {short && (
              <p>
                RESERVE_SHORT: requires {content.economy.vote.min_stock_days}{' '}
                days of stock
              </p>
            )}
            <button
              disabled={
                missing ||
                short ||
                !resident ||
                !vote.isSuccess ||
                !!run ||
                vote.data?.status === 'open' ||
                !!realm.pending_transition ||
                action.isPending
              }
              onClick={() =>
                ask(
                  `/upgrades/${encodeURIComponent(upgrade.id)}/call`,
                  {},
                  `Call vote? Pay ${upgrade.fee_gold} gold, not refunded even if the vote fails.`,
                )
              }
            >
              Call vote {upgrade.id}
            </button>
          </article>
        )
      })}
      {vote.isError && <p role="alert">{vote.error.message}</p>}
      {vote.data && (
        <VotePanel
          vote={vote.data}
          characterId={profile.character.id}
          pending={action.isPending}
          onExpire={() => {
            void client.invalidateQueries({ queryKey: ['realms', realm.id] })
          }}
          onCast={(choice) =>
            ask(
              '/vote',
              { choice },
              `Vote ${choice}? Your choice cannot be changed.`,
            )
          }
        />
      )}
      <h3>Estates</h3>
      {estates.isError && <p role="alert">{estates.error.message}</p>}
      {estates.data?.map((e) => (
        <p key={e.id}>
          {content.estate_forms.forms.find((f) => f.id === e.form)?.name ??
            e.form}{' '}
          · {e.owner} · {e.decay_stage} · {e.gauge} days{' '}
          {e.sale_price !== null && `· Sale: ${e.sale_price} gold`}
        </p>
      ))}
      <Link to="/estate">Manage estate / buy</Link>
      {confirmation && (
        <div role="dialog" aria-modal="true" aria-label="Confirm realm action">
          <p>{confirmation.message}</p>
          <button
            disabled={action.isPending}
            onClick={() =>
              action.mutate(confirmation, {
                onSuccess: () => {
                  setConfirmation(null)
                  if (confirmation.path.endsWith('/vote')) action.reset()
                },
              })
            }
          >
            Confirm
          </button>
          <button
            disabled={action.isPending}
            onClick={() => setConfirmation(null)}
          >
            Cancel
          </button>
        </div>
      )}
      {action.error && <p role="alert">{action.error.message}</p>}
    </>
  )
}
