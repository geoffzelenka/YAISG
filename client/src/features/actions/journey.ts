import type { ActiveAction } from '../../api/actions'

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function journeyStep(
  active: ActiveAction,
): { index: number; count: number; edge: string; remaining: number } | null {
  const meta = active.meta
  if (
    !meta ||
    !Array.isArray(meta.route) ||
    typeof meta.step_index !== 'number' ||
    typeof meta.remaining_ms !== 'number'
  )
    return null
  const step: unknown = meta.route[meta.step_index]
  if (!isRecord(step) || typeof step.edge_id !== 'string') return null
  return {
    index: meta.step_index + 1,
    count: meta.route.length,
    edge: step.edge_id,
    remaining: meta.remaining_ms,
  }
}
