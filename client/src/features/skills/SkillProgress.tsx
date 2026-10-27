import type { CharacterProfile } from '../../api/characters'

export function SkillProgress({
  skill,
}: {
  skill: CharacterProfile['skills'][number]
}) {
  return (
    <p>
      Level {skill.level} ·{' '}
      <span aria-label="Skill tier">
        Tier {skill.tier}: {skill.tier_title}
      </span>{' '}
      ·{' '}
      {skill.xp_to_next === null
        ? 'Maximum level'
        : `${skill.xp_to_next} XP to next`}
    </p>
  )
}
