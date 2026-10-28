import type { ActiveAction } from '../../api/actions'

import {
  resolutionPresentation,
  resolverResolutions,
} from './resolverPresentation'
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
  realmNames = new Map<string, string>(),
}: {
  details?: Record<string, unknown>
  realmNames?: Map<string, string>
}) {
  return (
    <div>
      {resolverResolutions(details).map((value, index) => {
        const { travel, extra } = resolutionPresentation(value)
        return (
          <div key={index}>
            {isRecord(value) && typeof value.kills === 'number' && (
              <h3>Combat summary</h3>
            )}
            {travel && travel.edges > 0 && (
              <p>
                Travel: {travel.edges} edges completed · Current realm:{' '}
                {realmNames.get(travel.realmId) ?? travel.realmId}
              </p>
            )}
            {Object.keys(extra).length > 0 && <DetailValue value={extra} />}
          </div>
        )
      })}
    </div>
  )
}
