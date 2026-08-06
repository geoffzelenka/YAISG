import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'

import {
  fetchAction,
  type ActionFeedResponse,
  type Rewards,
  useStopAction,
} from '../../api/actions'
import { useContent } from '../../api/content'
import {
  cycleProgress,
  nextCycleDelay,
  startActionClock,
  useActionClock,
} from './actionStore'
import { shouldShowWelcomeBack } from './rewardPresentation'

type FeedEntry = {
  id: number
  rewards: Rewards
  reason: string | null
  showToast: boolean
  toastUntil: number
}

function hasAuthoritativeChanges(response: ActionFeedResponse): boolean {
  const rewards = response.since_last
  return (
    rewards.cycles_completed > 0 ||
    Object.keys(rewards.items_gained).length > 0 ||
    Object.keys(rewards.items_consumed).length > 0
  )
}

export function ActionExperience() {
  const client = useQueryClient()
  const content = useContent()
  const stop = useStopAction()
  const actionQuery = useQuery({
    queryKey: ['characters', 'me', 'action'],
    queryFn: fetchAction,
    enabled: false,
  })
  const [feed, setFeed] = useState<FeedEntry[]>([])
  const [welcome, setWelcome] = useState<Rewards | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const nextFeedId = useRef(0)
  const now = useActionClock((state) => state.now)

  useEffect(() => startActionClock(), [])

  const mergeResponse = useCallback(
    (next: ActionFeedResponse) => {
      client.setQueryData(['characters', 'me', 'action'], next)
      const isWelcomeBack = shouldShowWelcomeBack(next.since_last)
      if (isWelcomeBack) setWelcome(next.since_last)
      if (next.since_last.cycles_completed > 0 || next.stop_reason !== null) {
        setFeed((current) =>
          [
            ...current,
            {
              id: (nextFeedId.current += 1),
              rewards: next.since_last,
              reason: next.stop_reason,
              showToast: !isWelcomeBack,
              toastUntil: Date.now() + 5_000,
            },
          ].slice(-30),
        )
      }
      if (hasAuthoritativeChanges(next)) {
        void client.invalidateQueries({
          queryKey: ['characters', 'me'],
          exact: true,
        })
        void client.invalidateQueries({
          queryKey: ['characters', 'me', 'inventory'],
        })
        void client.invalidateQueries({
          queryKey: ['characters', 'me', 'actions', 'available'],
        })
      }
    },
    [client],
  )

  useEffect(() => {
    const receiveRelocationRewards = (event: Event) => {
      const rewards = (event as CustomEvent<Rewards>).detail
      const isWelcomeBack = shouldShowWelcomeBack(rewards)
      if (isWelcomeBack) setWelcome(rewards)
      setFeed((current) =>
        [
          ...current,
          {
            id: (nextFeedId.current += 1),
            rewards,
            reason: rewards.stop_reason ?? 'Action stopped for relocation',
            showToast: !isWelcomeBack,
            toastUntil: Date.now() + 5_000,
          },
        ].slice(-30),
      )
    }
    window.addEventListener(
      'yaisg:relocation-rewards',
      receiveRelocationRewards,
    )
    return () =>
      window.removeEventListener(
        'yaisg:relocation-rewards',
        receiveRelocationRewards,
      )
  }, [])

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout> | undefined
    let cancelled = false
    let inFlight = false
    let lastActive: ActionFeedResponse['active'] | undefined
    const schedule = () => {
      if (cancelled) return
      timeout = setTimeout(
        () => void poll(),
        lastActive
          ? nextCycleDelay(
              Date.now(),
              lastActive.started_at,
              lastActive.cycle_ms,
            )
          : 30_000,
      )
    }
    const poll = async () => {
      if (inFlight || cancelled) return
      inFlight = true
      if (timeout !== undefined) clearTimeout(timeout)
      try {
        const next = await client.fetchQuery({
          queryKey: ['characters', 'me', 'action'],
          queryFn: fetchAction,
        })
        if (cancelled) return
        lastActive = next.active ?? undefined
        mergeResponse(next)
      } catch {
        // TanStack Query exposes the failure state; keep the loop alive so a
        // transient network error does not disable catch-up polling.
      } finally {
        inFlight = false
        schedule()
      }
    }
    void poll()
    const refresh = () => {
      void client.invalidateQueries({
        queryKey: ['characters', 'me'],
        exact: true,
      })
      void client.invalidateQueries({
        queryKey: ['characters', 'me', 'inventory'],
      })
      void poll()
    }
    window.addEventListener('focus', refresh)
    window.addEventListener('online', refresh)
    window.addEventListener('yaisg:action-changed', refresh)
    return () => {
      cancelled = true
      if (timeout !== undefined) clearTimeout(timeout)
      window.removeEventListener('focus', refresh)
      window.removeEventListener('online', refresh)
      window.removeEventListener('yaisg:action-changed', refresh)
    }
  }, [client, mergeResponse])

  const active = actionQuery.data?.active ?? null
  const action =
    content.status === 'ready' && active
      ? content.content.skills.skills
          .flatMap((skill) => skill.actions)
          .find((candidate) => candidate.id === active.action_id)
      : undefined
  const progress = active
    ? cycleProgress(now, active.started_at, active.cycle_ms)
    : 0
  const itemNames =
    content.status === 'ready'
      ? new Map(content.content.items.items.map((item) => [item.id, item.name]))
      : new Map<string, string>()
  const skillNames =
    content.status === 'ready'
      ? new Map(
          content.content.skills.skills.map((skill) => [skill.id, skill.name]),
        )
      : new Map<string, string>()
  const displayNames = { itemNames, skillNames }

  return (
    <>
      <section
        className="border-t border-slate-700 bg-slate-900 px-6 py-4"
        aria-label="Active action"
      >
        <div className="flex items-center gap-4">
          <span
            className="grid size-10 place-items-center rounded bg-slate-800"
            aria-hidden="true"
          >
            ◇
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex justify-between gap-3">
              <strong>
                {active
                  ? (action?.name ?? active.action_id)
                  : 'No active action'}
              </strong>
              <span className="text-xs text-slate-400">Cosmetic timer</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded bg-slate-700">
              <div
                className="h-full bg-emerald-400 transition-[width] duration-200"
                data-testid="action-progress"
                style={{ width: `${progress * 100}%` }}
              />
            </div>
          </div>
          <button
            className="secondary-button"
            disabled={!active || stop.isPending}
            onClick={() =>
              stop.mutate(undefined, {
                onSuccess: (next) => {
                  mergeResponse(next)
                  window.dispatchEvent(new Event('yaisg:action-changed'))
                },
              })
            }
          >
            Stop
          </button>
          <button
            className="secondary-button"
            aria-expanded={drawerOpen}
            onClick={() => setDrawerOpen((open) => !open)}
          >
            Rewards ({feed.length})
          </button>
        </div>
        {drawerOpen && <RewardList entries={feed} />}
        {stop.error && (
          <p className="mt-3 text-red-300" role="alert">
            {stop.error.message}
          </p>
        )}
      </section>
      <div className="fixed right-4 top-4 z-40 space-y-2" aria-live="polite">
        {feed
          .filter((entry) => entry.showToast && entry.toastUntil > now)
          .slice(-3)
          .map((entry) => (
            <RewardSummary key={entry.id} entry={entry} names={displayNames} />
          ))}
      </div>
      {welcome && (
        <WelcomeBack
          rewards={welcome}
          names={displayNames}
          onClose={() => setWelcome(null)}
        />
      )}
    </>
  )
}

type DisplayNames = {
  itemNames: Map<string, string>
  skillNames: Map<string, string>
}

function RewardList({ entries }: { entries: FeedEntry[] }) {
  const content = useContent()
  const names: DisplayNames = {
    itemNames:
      content.status === 'ready'
        ? new Map(
            content.content.items.items.map((item) => [item.id, item.name]),
          )
        : new Map<string, string>(),
    skillNames:
      content.status === 'ready'
        ? new Map(
            content.content.skills.skills.map((skill) => [
              skill.id,
              skill.name,
            ]),
          )
        : new Map<string, string>(),
  }
  return (
    <div className="mt-4 max-h-40 overflow-auto border-t border-slate-700 pt-3">
      {entries.length === 0 ? (
        <p className="text-sm text-slate-400">No rewards received yet.</p>
      ) : (
        [...entries]
          .reverse()
          .map((entry) => (
            <RewardSummary key={entry.id} entry={entry} names={names} />
          ))
      )}
    </div>
  )
}

function RewardSummary({
  entry,
  names,
}: {
  entry: FeedEntry
  names: DisplayNames
}) {
  const text = summarize(entry.rewards, names)
  return (
    <div className="rounded border border-slate-700 bg-slate-950 p-3 text-sm">
      {text || 'Action ended.'}
      {entry.reason && (
        <p className="text-amber-300">
          Stopped: {entry.reason.replaceAll('_', ' ')}
        </p>
      )}
    </div>
  )
}

function summarize(rewards: Rewards, names: DisplayNames): string {
  const parts = Object.entries(rewards.items_gained).map(
    ([id, qty]) => `+${qty} ${names.itemNames.get(id) ?? id}`,
  )
  parts.push(
    ...Object.entries(rewards.xp_gained).map(
      ([id, xp]) => `+${xp} ${names.skillNames.get(id) ?? id} XP`,
    ),
    ...Object.entries(rewards.overflowed_items).map(
      ([id, qty]) => `${qty} ${names.itemNames.get(id) ?? id} overflowed`,
    ),
    ...Object.entries(rewards.level_ups).map(
      ([id, levels]) =>
        `${names.skillNames.get(id) ?? id} reached level ${levels.at(-1) ?? ''}`,
    ),
  )
  return parts.join(' · ')
}

export function WelcomeBack({
  rewards,
  names = { itemNames: new Map(), skillNames: new Map() },
  onClose,
}: {
  rewards: Rewards
  names?: DisplayNames
  onClose: () => void
}) {
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose])
  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-slate-950/80 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="welcome-title"
    >
      <div className="w-full max-w-lg rounded-xl border border-emerald-500 bg-slate-900 p-6">
        <h2 id="welcome-title" className="text-2xl font-bold text-emerald-300">
          Welcome back
        </h2>
        <p className="mt-2">{rewards.cycles_completed} cycles completed.</p>
        <dl className="mt-4 space-y-2">
          {Object.entries(rewards.xp_gained).map(([skill, xp]) => (
            <div key={skill}>
              <dt className="inline">
                {names.skillNames.get(skill) ?? skill} XP:{' '}
              </dt>
              <dd className="inline">{xp}</dd>
            </div>
          ))}
          {Object.entries(rewards.items_gained).map(([item, qty]) => (
            <div key={item}>
              <dt className="inline">{names.itemNames.get(item) ?? item}: </dt>
              <dd className="inline">{qty}</dd>
            </div>
          ))}
        </dl>
        {Object.entries(rewards.overflowed_items).map(([item, qty]) => (
          <p className="mt-2 text-amber-300" key={item}>
            {qty} {names.itemNames.get(item) ?? item} could not fit.
          </p>
        ))}
        {Object.entries(rewards.level_ups).map(([skill, levels]) => (
          <p className="mt-2 text-emerald-300" key={skill}>
            {names.skillNames.get(skill) ?? skill} reached level {levels.at(-1)}
            .
          </p>
        ))}
        {rewards.stop_reason && (
          <p className="mt-4 text-amber-300">
            Stopped: {rewards.stop_reason.replaceAll('_', ' ')}
          </p>
        )}
        <button autoFocus className="primary-button mt-6" onClick={onClose}>
          Continue
        </button>
      </div>
    </div>
  )
}
