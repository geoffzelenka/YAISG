import type { Project } from '../../api/content'
import type { RealmDetail } from '../../api/realms'

export function kickoffReason(
  project: Project,
  realm: RealmDetail,
  resident: boolean,
  openVote: boolean,
): string | null {
  const tags = new Set([...realm.node.tags, ...realm.tags.map((t) => t.tag_id)])
  if (project.kickoff.who === 'residents' && !resident)
    return 'Only residents may kick off'
  if (tags.has(project.grants_tag)) return 'Tag already held'
  if (project.requires_tags.some((t) => !tags.has(t)))
    return 'Required tags missing'
  if (realm.active_run) return 'Another project is active'
  if (openVote) return 'A vote is open'
  if (realm.pending_transition) return 'Realm is transitioning'
  if (realm.lines.some((line) => line.stock <= 0))
    return 'RESERVE_SHORT: every demand line needs positive stock'
  return null
}
