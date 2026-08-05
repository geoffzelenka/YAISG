import {
  ActionApiError,
  useAvailableActions,
  useStartAction,
} from '../../api/actions'
import { useContent } from '../../api/content'

export function SkillPanel({ skillId }: { skillId: string }) {
  const available = useAvailableActions()
  const content = useContent()
  const start = useStartAction()
  if (available.isPending || content.status === 'loading')
    return <p>Loading actions…</p>
  if (available.isError || content.status === 'error')
    return <p className="text-red-300">Unable to load actions.</p>
  const group = available.data.skills.find(
    (skill) => skill.skill_id === skillId,
  )
  const contentSkill = content.content.skills.skills.find(
    (skill) => skill.id === skillId,
  )
  const items = new Map(
    content.content.items.items.map((item) => [item.id, item.name]),
  )
  if (!group || !contentSkill)
    return <p>This skill has no available actions.</p>
  return (
    <section>
      <h2 className="text-3xl font-bold">{group.name}</h2>
      {start.error && (
        <p className="mt-4 text-red-300" role="alert">
          {start.error instanceof ActionApiError
            ? start.error.message
            : 'Unable to start action.'}
        </p>
      )}
      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        {group.actions.map((action) => {
          const definition = contentSkill.actions.find(
            (candidate) => candidate.id === action.action_id,
          )
          return (
            <article
              key={action.action_id}
              className={`rounded-xl border bg-slate-900 p-5 ${action.startable ? 'border-slate-700' : 'border-slate-800 opacity-70'}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-semibold">{action.name}</h3>
                  <p className="text-sm text-slate-400">
                    Level {action.level_required} ·{' '}
                    {(action.cycle_ms / 1000).toFixed(2)}s effective cycle
                  </p>
                </div>
                <button
                  className="primary-button"
                  disabled={!action.startable || start.isPending}
                  onClick={() => start.mutate(action.action_id)}
                >
                  Start
                </button>
              </div>
              <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <Recipe
                  title="Inputs"
                  values={
                    definition?.inputs.map(
                      (input) =>
                        `${input.qty}× ${items.get(input.item_id) ?? input.item_id}`,
                    ) ?? []
                  }
                />
                <Recipe
                  title="Outputs"
                  values={
                    definition?.drops.map(
                      (drop) =>
                        `${drop.qty[0]}–${drop.qty[1]}× ${items.get(drop.item_id) ?? drop.item_id} (${(drop.chance * 100).toFixed(0)}%)`,
                    ) ?? []
                  }
                />
              </div>
              {!action.startable && (
                <p className="mt-4 text-amber-300">
                  Locked: {action.blocked_by.map(formatBlocker).join(', ')}
                </p>
              )}
            </article>
          )
        })}
      </div>
    </section>
  )
}

function Recipe({ title, values }: { title: string; values: string[] }) {
  return (
    <div>
      <h4 className="font-semibold text-slate-300">{title}</h4>
      {values.length ? (
        <ul className="mt-1 text-slate-400">
          {values.map((value) => (
            <li key={value}>{value}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-1 text-slate-500">None</p>
      )}
    </div>
  )
}

function formatBlocker(value: string): string {
  return value.toLowerCase().replaceAll('_', ' ')
}
