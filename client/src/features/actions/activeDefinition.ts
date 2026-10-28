import type { ActiveAction } from '../../api/actions'
import type { Action } from '../../api/content'
import { isRecord } from './journey'

/** Private key actions carry their authoritative definition beside the key id. */
export function activeDefinition(
  active: ActiveAction | null | undefined,
  actions: Action[],
): Action | undefined {
  const keyAction = active?.meta?.key_action
  if (
    typeof active?.meta?.key_id === 'string' &&
    isRecord(keyAction) &&
    typeof keyAction.id === 'string' &&
    (keyAction.resolver === 'combat' || keyAction.resolver === 'uniform')
  )
    return keyAction as Action
  return actions.find((action) => action.id === active?.action_id)
}
