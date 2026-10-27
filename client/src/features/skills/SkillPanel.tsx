import {
  ActionApiError,
  useAvailableActions,
  useStartAction,
} from '../../api/actions'
import { SkillProgress } from './SkillProgress'
import { Link } from 'react-router-dom'
import { useCharacterProfile } from '../../api/characters'
import { useContent } from '../../api/content'

export function SkillPanel({ skillId }: { skillId: string }) {
  const profile = useCharacterProfile()
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
      {profile.data?.skills
        .filter((skill) => skill.id === skillId)
        .map((skill) => <SkillProgress key={skill.id} skill={skill} />)}
      {skillId === 'travel' && (
        <Link to="/realm/map">Plan a journey on the map</Link>
      )}
      {start.error && (
        <p className="mt-4 text-red-300" role="alert">
          {start.error instanceof ActionApiError
            ? start.error.message
            : 'Unable to start action.'}
        </p>
      )}
      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        {group.actions
          .filter(() => skillId !== 'travel')
          .map((action) => {
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
                      Level {action.unlock_level} ·{' '}
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
                <p>
                  {action.xp_per_cycle} XP per cycle · Proficiency{' '}
                  {action.proficiency_pct?.toFixed(1)}% · Taper ×
                  {action.taper_factor}
                </p>
                <p>
                  XP bonus: {action.xp_bonus_capped?.toFixed(1)}% (uncapped{' '}
                  {action.xp_bonus_uncapped?.toFixed(1)}%){' '}
                  {action.xp_bonus_uncapped > action.xp_bonus_capped && (
                    <strong>XP capped</strong>
                  )}
                </p>
                <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                  <Recipe
                    title="Inputs"
                    values={
                      definition?.inputs.map(
                        (input) =>
                          `${input.quantity}× ${input.selector.item ? (items.get(input.selector.item) ?? input.selector.item) : `${input.selector.class}${input.selector.tier ? ` (tier ${input.selector.tier})` : ''}`}`,
                      ) ?? []
                    }
                  />
                  <Recipe
                    title="Outputs"
                    values={
                      definition?.outputs.map(
                        (drop) =>
                          `${drop.quantity_min}–${drop.quantity_max}× ${items.get(drop.item_id) ?? drop.item_id} (${(drop.chance * 100).toFixed(0)}%)`,
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
  const reasons: Record<string, string> = {
    INSUFFICIENT_LEVEL: 'insufficient level',
    NOT_OFFERED_HERE: 'Not offered in this realm',
    MISSING_FACILITY: 'Required facility is unavailable',
    MISSING_REALM_TAG: 'Required realm feature is unavailable',
    MISSING_SKILL_LEVEL: 'Required skill level has not been reached',
    MISSING_TOOL: 'Required tool is not equipped',
    MISSING_INPUTS: 'Not enough supplies',
    TRAVEL_DESTINATION_REQUIRED: 'Choose a destination on the map',
  }
  return reasons[value] ?? value.toLowerCase().replaceAll('_', ' ')
}
