import { Link, useSearchParams } from 'react-router-dom'
import type { CharacterProfile } from '../../api/characters'
import { useRealmMap } from '../../api/realms'
import { useWorldMarkets } from '../../api/realmMarket'
import { selectorLabel } from './presentation'
import { TravelForm } from './TravelForm'

export function MapPanel({ profile }: { profile: CharacterProfile }) {
  const [search] = useSearchParams()
  const destination = search.get('destination') ?? ''
  const map = useRealmMap()
  const markets = useWorldMarkets(
    map.data?.nodes.map((node) => node.realm_id) ?? [],
  )
  if (map.isPending) return <p>Loading map…</p>
  if (map.isError) return <p className="text-red-300">Unable to load map.</p>
  return (
    <section>
      <h2 className="text-3xl font-bold">Realm map</h2>
      <TravelForm
        key={`${profile.character.current_realm_id}:${destination}`}
        initialDestination={destination}
        profile={profile}
        nodes={map.data.nodes}
      />
      <p className="mt-2 text-slate-400">Travel routes connect the realms.</p>
      <ul className="mt-4" aria-label="Realm health">
        {map.data.nodes.map((node) => (
          <li key={node.realm_id}>
            {node.name} · Tier {node.tier} · {node.decay_stage} · Gauge:{' '}
            {node.gauge.toFixed(2)} days
            {node.treasury_band && ` · Treasury: ${node.treasury_band}`}
            {node.transition_pending && ' · Transition pending'}
          </li>
        ))}
      </ul>
      <h3 className="mt-6 text-xl">Hungry realms</h3>
      <p>Highest gauge first. Short lines are below reserve.</p>
      {markets.every(
        (market) =>
          market.isSuccess &&
          !market.data.lines.some((line) => line.stock < line.reserve),
      ) && <p>No realm is below reserve.</p>}
      <ul>
        {[...map.data.nodes]
          .sort(
            (a, b) =>
              b.gauge - a.gauge ||
              (a.realm_id < b.realm_id ? -1 : a.realm_id > b.realm_id ? 1 : 0),
          )
          .map((node) => {
            const market = markets[map.data.nodes.indexOf(node)]
            if (
              market?.data &&
              !market.data.lines.some((line) => line.stock < line.reserve)
            )
              return null
            return (
              <li key={node.realm_id}>
                <Link
                  to={`/realm/market?realm=${encodeURIComponent(node.realm_id)}`}
                >
                  {node.name}
                </Link>{' '}
                · Gauge: {node.gauge.toFixed(2)} days
                {market?.isError ? (
                  ' · Unable to load short lines.'
                ) : !market?.data ? (
                  ' · Loading short lines…'
                ) : (
                  <ul>
                    {market.data.lines
                      .filter((line) => line.stock < line.reserve)
                      .map((line) => (
                        <li key={line.line_key}>
                          {selectorLabel(line.selector)}: short{' '}
                          {(line.reserve - line.stock) / 1000} line units
                        </li>
                      ))}
                  </ul>
                )}
              </li>
            )
          })}
      </ul>
      <svg
        aria-label="Realm graph"
        className="mt-6 w-full rounded-xl border border-slate-700 bg-slate-900"
        viewBox="0 0 540 460"
      >
        {map.data.edges.map((edge) => {
          const from = map.data.nodes.find(
            (node) => node.realm_id === edge.a && node.position !== null,
          )
          const to = map.data.nodes.find(
            (node) => node.realm_id === edge.b && node.position !== null,
          )
          if (!from?.position || !to?.position) return null
          const summary = `${edge.terrain}, ${edge.base_time_s}s`
          return (
            <line
              key={edge.id}
              stroke="#64748b"
              strokeWidth="4"
              x1={from.position.x}
              y1={from.position.y}
              x2={to.position.x}
              y2={to.position.y}
            >
              <title>{summary}</title>
            </line>
          )
        })}
        {map.data.nodes.map((node) => {
          if (node.position === null) return null
          const current = node.realm_id === profile.character.current_realm_id
          return (
            <g key={node.realm_id}>
              <circle
                cx={node.position.x}
                cy={node.position.y}
                fill={current ? '#34d399' : '#334155'}
                r="42"
                stroke="#94a3b8"
                strokeWidth="4"
              />
              <text
                fill={current ? '#020617' : '#f8fafc'}
                fontSize="13"
                textAnchor="middle"
                x={node.position.x}
                y={node.position.y + 4}
              >
                {node.name}
              </text>
            </g>
          )
        })}
      </svg>
    </section>
  )
}
