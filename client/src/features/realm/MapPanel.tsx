import type { CharacterProfile } from '../../api/characters'
import { useRealmMap } from '../../api/realms'

export function MapPanel({ profile }: { profile: CharacterProfile }) {
  const map = useRealmMap()
  if (map.isPending) return <p>Loading map…</p>
  if (map.isError) return <p className="text-red-300">Unable to load map.</p>
  return (
    <section>
      <h2 className="text-3xl font-bold">Realm map</h2>
      <p className="mt-2 text-slate-400">Travel routes connect the realms.</p>
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
