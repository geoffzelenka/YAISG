import {
  Navigate,
  NavLink,
  Outlet,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'

import { useCurrentPlayer } from './api/players'
import { AuthForm } from './features/auth/AuthForm'
import { useAuth } from './features/auth/AuthProvider'

const sections = [
  'Profile',
  'Player Market',
  'Realm Market',
  'Estate',
  'Combat',
  'Gathering',
  'Refining',
  'Crafting',
]

function RequireAuth() {
  const { state } = useAuth()
  const location = useLocation()
  if (state === 'loading') {
    return (
      <p className="grid min-h-screen place-items-center">Restoring session…</p>
    )
  }
  return state === 'authenticated' ? (
    <Outlet />
  ) : (
    <Navigate to="/login" state={{ from: location.pathname }} replace />
  )
}

function Shell() {
  const { logout } = useAuth()
  const player = useCurrentPlayer()
  return (
    <div className="grid min-h-screen md:grid-cols-[15rem_1fr]">
      <aside className="border-r border-slate-800 bg-slate-900 p-5">
        <h1 className="text-xl font-bold text-emerald-400">YAISG</h1>
        <nav className="mt-8 space-y-1" aria-label="Game sections">
          {sections.map((section) => (
            <NavLink className="sidebar-link" key={section} to="/">
              {section}
            </NavLink>
          ))}
          <span className="sidebar-link cursor-not-allowed text-slate-600">
            Exploration · coming soon
          </span>
        </nav>
        <button
          className="secondary-button mt-8 w-full"
          onClick={() => void logout()}
        >
          Log out
        </button>
      </aside>
      <main className="p-8">
        <h2 className="text-3xl font-bold">Authenticated shell</h2>
        <p className="mt-2 text-slate-400">All game panels are coming soon.</p>
        <section className="mt-8 rounded-xl border border-slate-700 bg-slate-900 p-6">
          <h3 className="font-semibold text-emerald-400">Player API</h3>
          {player.isPending && <p className="mt-2">Loading player…</p>}
          {player.isError && (
            <p className="mt-2 text-red-300">Unable to load player.</p>
          )}
          {player.data && (
            <p className="mt-2 font-mono text-sm">Player {player.data.id}</p>
          )}
        </section>
        <div className="mt-8 border-t border-slate-800 pt-4 text-sm text-slate-500">
          Current action · coming soon
        </div>
      </main>
    </div>
  )
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthForm mode="login" />} />
      <Route path="/register" element={<AuthForm mode="register" />} />
      <Route element={<RequireAuth />}>
        <Route path="/" element={<Shell />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
