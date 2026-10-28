import { expect, it } from 'vitest'
import type { Action } from '../../api/content'
import { activeDefinition } from './activeDefinition'
it('recognizes private combat key identity without a public action definition', () => {
  const definition = { id: 'template', resolver: 'combat' } as Action
  const active = {
    action_id: 'template',
    cycle_ms: 1000,
    started_at: '',
    last_resolved_at: '',
    meta: { key_id: 'instance', key_action: definition },
  }
  expect(activeDefinition(active, [])).toEqual(definition)
  expect(activeDefinition({ ...active, meta: {} }, [])).toBeUndefined()
})
