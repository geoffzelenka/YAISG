import type { ActiveAction } from '../../api/actions'

import { isRecord, journeyStep } from './journey'

export function JourneyProgress({ active }: { active: ActiveAction }) {
  const step = journeyStep(active)
  return (
    step && (
      <p>
        Journey step {step.index} of {step.count} · Current edge: {step.edge}
      </p>
    )
  )
}

/** Preserve unknown resolver payloads as readable nested data. */
function DetailValue({ value }: { value: unknown }) {
  if (Array.isArray(value))
    return (
      <ul>
        {value.map((entry: unknown, index) => (
          <li key={index}>
            <DetailValue value={entry} />
          </li>
        ))}
      </ul>
    )
  if (isRecord(value))
    return (
      <dl>
        {Object.entries(value).map(([key, entry]) => (
          <div key={key}>
            <dt>{key.replaceAll('_', ' ')}</dt>
            <dd>
              <DetailValue value={entry} />
            </dd>
          </div>
        ))}
      </dl>
    )
  return <span>{value === null ? 'None' : String(value)}</span>
}

export function ResolverDetails({
  details,
}: {
  details?: Record<string, unknown>
}) {
  if (!details || !Object.keys(details).length) return null
  const resolutions = Array.isArray(details.resolutions)
    ? details.resolutions
    : [details]
  return (
    <div>
      {resolutions.map((value: unknown, index) => (
        <div key={index}>
          {isRecord(value) && Array.isArray(value.edges_completed) && (
            <p>
              Travel: {value.edges_completed.length} edges completed · Current
              realm: {String(value.current_realm_id ?? '')}
            </p>
          )}
          <DetailValue value={value} />
        </div>
      ))}
    </div>
  )
}
