import { useEffect, useState } from 'react'

type Health = {
  service: string
  status: 'ok'
  version: string
}

type ServiceHealth =
  | { state: 'loading' }
  | { state: 'healthy'; health: Health }
  | { state: 'unavailable' }

const services = [
  {
    name: 'Game service',
    url: `${import.meta.env.VITE_GAME_URL ?? 'http://localhost:8000'}/healthz`,
  },
  {
    name: 'Auth service',
    url: `${import.meta.env.VITE_AUTH_URL ?? 'http://localhost:8001'}/healthz`,
  },
]

const statusColors: Record<ServiceHealth['state'], string> = {
  loading: 'bg-slate-500',
  healthy: 'bg-emerald-400',
  unavailable: 'bg-amber-400',
}

function HealthCard({ name, url }: { name: string; url: string }) {
  const [health, setHealth] = useState<ServiceHealth>({ state: 'loading' })

  useEffect(() => {
    const controller = new AbortController()

    async function loadHealth() {
      try {
        const response = await fetch(url, { signal: controller.signal })
        if (!response.ok) {
          throw new Error(
            `Health request failed with status ${response.status}`,
          )
        }
        const data = (await response.json()) as Health
        setHealth({ state: 'healthy', health: data })
      } catch (error) {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          setHealth({ state: 'unavailable' })
        }
      }
    }

    void loadHealth()
    return () => controller.abort()
  }, [url])

  return (
    <article className="rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-lg">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold">{name}</h2>
        <span
          className={`h-3 w-3 rounded-full ${statusColors[health.state]}`}
          aria-label={`${name}: ${health.state}`}
        />
      </div>
      <p className="mt-3 text-sm text-slate-300" aria-live="polite">
        {health.state === 'loading' && 'Checking…'}
        {health.state === 'unavailable' && 'Unavailable'}
        {health.state === 'healthy' &&
          `Healthy · version ${health.health.version}`}
      </p>
    </article>
  )
}

export function App() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col justify-center px-6 py-16">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-400">
        System status
      </p>
      <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">
        Yet Another Idle Skilling Game
      </h1>
      <div className="mt-10 grid gap-4 sm:grid-cols-2">
        {services.map((service) => (
          <HealthCard key={service.name} {...service} />
        ))}
      </div>
    </main>
  )
}
