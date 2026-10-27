import { useState } from 'react'
import {
  Navigate,
  NavLink,
  Outlet,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'

import {
  CharacterApiError,
  type CharacterProfile,
  useCharacterProfile,
  useCreateCharacter,
} from './api/characters'
import { type Modifier, useContent } from './api/content'
import { AuthForm } from './features/auth/AuthForm'
import { useAuth } from './features/auth/AuthProvider'
import { ActionExperience } from './features/actions/ActionExperience'
import { InventoryPanel } from './features/profile/InventoryPanel'
import { SkillPanel } from './features/skills/SkillPanel'
import { EstatePanel } from './features/estate/EstatePanel'
import { MapPanel } from './features/realm/MapPanel'
import { PendingRelocationBanner } from './features/realm/PendingRelocationBanner'
import { RealmPanel, TransitionBanner } from './features/realm/RealmPanel'
import { useRealm } from './api/realms'

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

function describeModifier(modifier: Modifier): string {
  const labels: Record<Modifier['type'], string> = {
    cycle_time_pct: 'cycle time',
    xp_pct: 'XP',
    extra_drop_chance_pct: 'extra drop chance',
    market_tax_pct: 'market tax',
  }
  const prefix = modifier.value > 0 ? '+' : ''
  const skill = modifier.skill_id ? ` (${modifier.skill_id})` : ''
  return `${prefix}${modifier.value}% ${labels[modifier.type]}${skill}`
}

function CharacterCreation() {
  const content = useContent()
  const create = useCreateCharacter()
  const [name, setName] = useState('')
  const [realmId, setRealmId] = useState('')
  if (content.status === 'loading') return <p>Loading realms…</p>
  if (content.status === 'error') return <p>Unable to load realms.</p>
  const realms = content.content.realms.realms
  const selectedRealm = realmId || realms[0]?.id || ''
  return (
    <main className="mx-auto min-h-screen max-w-3xl p-8">
      <h1 className="text-3xl font-bold text-emerald-400">
        Create your character
      </h1>
      <p className="mt-2 text-slate-400">
        Choose a name and a realm for your estate.
      </p>
      <form
        className="mt-8 space-y-6"
        onSubmit={(event) => {
          event.preventDefault()
          create.mutate({ name: name.trim(), realm_id: selectedRealm })
        }}
      >
        <label className="block">
          <span>Character name</span>
          <input
            className="auth-input"
            minLength={3}
            maxLength={20}
            pattern="(?=.*[A-Za-z0-9])[A-Za-z0-9 ]+"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <fieldset>
          <legend className="mb-3 font-semibold">Starting realm</legend>
          <div className="grid gap-3 md:grid-cols-2">
            {realms.map((realm) => (
              <label
                className="cursor-pointer rounded-xl border border-slate-700 bg-slate-900 p-4 has-[:checked]:border-emerald-400"
                key={realm.id}
              >
                <input
                  className="mr-2"
                  type="radio"
                  name="realm"
                  value={realm.id}
                  checked={selectedRealm === realm.id}
                  onChange={() => setRealmId(realm.id)}
                />
                <strong>{realm.name}</strong>
                {(() => {
                  const node = content.content.development.nodes.find(
                    (candidate) => candidate.id === realm.starting_node_id,
                  )
                  return (
                    <>
                      <p className="mt-2 text-sm text-slate-400">
                        Tags: {node?.tags.join(', ') || 'none'}
                      </p>
                      <ul className="mt-2 text-sm text-slate-300">
                        {node?.modifiers.map((modifier, index) => (
                          <li key={`${modifier.type}-${index}`}>
                            {describeModifier(modifier)}
                          </li>
                        ))}
                      </ul>
                    </>
                  )
                })()}
              </label>
            ))}
          </div>
        </fieldset>
        {create.error && (
          <p className="text-red-300" role="alert">
            {create.error instanceof CharacterApiError
              ? create.error.message
              : 'Unable to create character.'}
          </p>
        )}
        <button
          className="primary-button"
          disabled={create.isPending || !selectedRealm}
        >
          {create.isPending ? 'Creating…' : 'Create character'}
        </button>
      </form>
    </main>
  )
}

export function ProfilePanel({ profile }: { profile: CharacterProfile }) {
  const realm = useRealm(profile.character.realm_id)
  const content = useContent()
  const currentNode =
    content.status === 'ready' && realm.data
      ? content.content.development.nodes.find(
          (node) => node.id === realm.data.node.id,
        )
      : undefined
  return (
    <section>
      {realm.data?.pending_transition && (
        <TransitionBanner
          realmId={realm.data.id}
          toNodeId={realm.data.pending_transition.to_node_id}
          completesAt={realm.data.pending_transition.completes_at}
        />
      )}
      <h2 className="text-3xl font-bold">{profile.character.name}</h2>
      <div className="mt-2 flex flex-wrap gap-3 text-slate-400">
        <span>{profile.realm.name}</span>
        <span>Gold: {profile.gold.toLocaleString()}</span>
        <span>Realm tags: {profile.realm.tags.join(', ')}</span>
      </div>
      {realm.data && (
        <div className="mt-5 rounded-lg border border-slate-700 bg-slate-900 p-4">
          <strong>
            {realm.data.node.name}
            {currentNode ? ` · ${currentNode.archetype}` : ''}
          </strong>
          <p className="mt-1 text-sm text-slate-400">
            Active modifiers:{' '}
            {profile.realm.active_modifiers.length
              ? profile.realm.active_modifiers.map(describeModifier).join(', ')
              : 'None'}
          </p>
        </div>
      )}
      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        {profile.skills.map((skill) => {
          const total = skill.xp_into_level + (skill.xp_to_next ?? 0)
          const percent =
            total === 0 ? 100 : (skill.xp_into_level / total) * 100
          return (
            <article
              className="rounded-xl border border-slate-700 bg-slate-900 p-5"
              key={skill.id}
            >
              <div className="flex justify-between">
                <h3 className="font-semibold">{skill.name}</h3>
                <span>Level {skill.level}</span>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded bg-slate-700">
                <div
                  className="h-full bg-emerald-400"
                  style={{ width: `${percent}%` }}
                />
              </div>
              <p className="mt-2 text-sm text-slate-400">
                {skill.xp_to_next === null
                  ? 'Maximum level'
                  : `${skill.xp_into_level} XP · ${skill.xp_to_next} to next`}
              </p>
            </article>
          )
        })}
      </div>
      <InventoryPanel />
    </section>
  )
}

function Shell({ profile }: { profile: CharacterProfile }) {
  const { logout } = useAuth()
  const groups: { name: string; path?: string }[][] = [
    [
      { name: 'Profile', path: '/' },
      { name: 'Player Market' },
      { name: 'Realm Market' },
      { name: 'Estate', path: '/estate' },
      { name: 'Realm', path: '/realm' },
      { name: 'Map', path: '/realm/map' },
    ],
    [{ name: 'Combat' }],
    [
      { name: 'Gathering', path: '/skills/gathering' },
      { name: 'Refining', path: '/skills/refining' },
      { name: 'Manufacturing', path: '/skills/manufacturing' },
    ],
  ]
  return (
    <div className="grid min-h-screen md:grid-cols-[15rem_1fr]">
      <aside className="border-r border-slate-800 bg-slate-900 p-5">
        <h1 className="text-xl font-bold text-emerald-400">YAISG</h1>
        <nav className="mt-8" aria-label="Game sections">
          {groups.map((group, groupIndex) => (
            <div
              className={
                groupIndex === 0 ? '' : 'mt-3 border-t border-slate-700 pt-3'
              }
              key={group[0].name}
            >
              {group.map((section) =>
                section.path ? (
                  <NavLink
                    end={section.path === '/'}
                    className={({ isActive }) =>
                      `sidebar-link ${isActive ? 'bg-slate-800 text-emerald-300' : ''}`
                    }
                    key={section.name}
                    to={section.path}
                  >
                    {section.name}
                  </NavLink>
                ) : (
                  <span
                    className="sidebar-link text-slate-500"
                    key={section.name}
                  >
                    {section.name} · coming soon
                  </span>
                ),
              )}
            </div>
          ))}
          <span
            aria-disabled="true"
            className="sidebar-link mt-3 cursor-not-allowed border-t border-slate-700 pt-5 text-slate-600"
          >
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
      <div className="flex min-h-screen min-w-0 flex-col">
        <main className="flex-1 p-8">
          <Routes>
            <Route index element={<ProfilePanel profile={profile} />} />
            <Route path="estate" element={<EstatePanel />} />
            <Route path="realm" element={<RealmPanel profile={profile} />} />
            <Route path="realm/map" element={<MapPanel profile={profile} />} />
            <Route
              path="skills/gathering"
              element={<SkillPanel skillId="gathering" />}
            />
            <Route
              path="skills/refining"
              element={<SkillPanel skillId="refining" />}
            />
            <Route
              path="skills/manufacturing"
              element={<SkillPanel skillId="manufacturing" />}
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <PendingRelocationBanner />
        <ActionExperience />
      </div>
    </div>
  )
}

function CharacterRouter() {
  const profile = useCharacterProfile()
  if (profile.isPending)
    return (
      <p className="grid min-h-screen place-items-center">Loading profile…</p>
    )
  if (profile.isError)
    return (
      <p className="grid min-h-screen place-items-center text-red-300">
        Unable to load profile.
      </p>
    )
  return profile.data === null ? (
    <CharacterCreation />
  ) : (
    <Shell profile={profile.data} />
  )
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthForm mode="login" />} />
      <Route path="/register" element={<AuthForm mode="register" />} />
      <Route element={<RequireAuth />}>
        <Route path="/*" element={<CharacterRouter />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
