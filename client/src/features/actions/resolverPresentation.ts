import { isRecord } from './journey'

/** Separate shared reward envelope fields from resolver-specific presentation. */
export function resolutionPresentation(value: unknown): {
  travel: { edges: number; realmId: string } | null
  extra: Record<string, unknown>
} {
  if (!isRecord(value)) return { travel: null, extra: {} }
  const isTravel = Array.isArray(value.edges_completed)
  const known = new Set(['level_ups', 'stop_reason'])
  if (isTravel) {
    for (const key of [
      'edges_completed',
      'current_realm_id',
      'supplies_used',
      'xp',
    ])
      known.add(key)
  }
  return {
    travel: isTravel
      ? {
          edges: (value.edges_completed as unknown[]).length,
          realmId: String(value.current_realm_id ?? ''),
        }
      : null,
    extra: Object.fromEntries(
      Object.entries(value).filter(([key]) => !known.has(key)),
    ),
  }
}

export function resolverResolutions(
  details?: Record<string, unknown>,
): unknown[] {
  if (!details) return []
  return Array.isArray(details.resolutions) ? details.resolutions : [details]
}

export function hasResolverContent(details?: Record<string, unknown>): boolean {
  return resolverResolutions(details).some((value) => {
    const { travel, extra } = resolutionPresentation(value)
    return (travel?.edges ?? 0) > 0 || Object.keys(extra).length > 0
  })
}
