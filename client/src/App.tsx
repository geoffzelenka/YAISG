import { useState } from 'react'
import { EquipmentPanel } from './features/equipment/EquipmentPanel'
import { CombatPanel } from './features/combat/CombatPanel'
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
import { RealmPanel, TransitionBanner } from './features/realm/RealmPanel'
import { GlobalMarketPanel } from './features/market/GlobalMarketPanel'
import { RealmMarketPanel } from './features/market/RealmMarketPanel'
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
    combat_accuracy_pct: 'combat accuracy',
    combat_power_pct: 'combat power',
    combat_defense_pct: 'combat defense',
    combat_armour_pct: 'combat armour',
    combat_hp_pct: 'maximum HP',
    journey_speed_pct: 'journey speed',
    supply_reduction_pct: 'supply reduction',
    cycle_speed_pct: 'cycle speed',
    xp_pct: 'XP',
    extra_drop_chance_pct: 'extra drop chance',
  }
  const prefix = modifier.value > 0 ? '+' : ''
  const skill = modifier.skill_id ? ` (${modifier.skill_id})` : ''
  return `${prefix}${modifier.value}% ${labels[modifier.type]}${skill}`
}

export function CharacterCreation() {
  const create = useCreateCharacter()
  const [name, setName] = useState('')
  return (
    <main className="mx-auto min-h-screen max-w-3xl p-8">
      <h1 className="text-3xl font-bold text-emerald-400">
        Create your character
      </h1>
      <p className="mt-2 text-slate-400">
        Choose a name to begin on Tutorial Island.
      </p>
      <form
        className="mt-8 space-y-6"
        onSubmit={(event) => {
          event.preventDefault()
          create.mutate({ name: name.trim() })
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

        {create.error && (
          <p className="text-red-300" role="alert">
            {create.error instanceof CharacterApiError
              ? create.error.message
              : 'Unable to create character.'}
          </p>
        )}
        <button className="primary-button" disabled={create.isPending}>
          {create.isPending ? 'Creating…' : 'Create character'}
        </button>
      </form>
    </main>
  )
}

export function ProfilePanel({ profile }: { profile: CharacterProfile }) {
  const realm = useRealm(profile.character.current_realm_id)
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
          toNodeId={realm.data.pending_transition.to_node}
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
            {currentNode ? ` · ${currentNode.realm_type}` : ''}
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
                <span>
                  Level {skill.level} · Tier {skill.tier}: {skill.tier_title}
                </span>
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
      { name: 'Player Market', path: '/market' },
      { name: 'Realm Market', path: '/realm/market' },
      { name: 'Estate', path: '/estate' },
      { name: 'Realm', path: '/realm' },
      { name: 'Map', path: '/realm/map' },
    ],
    [
      { name: 'Combat', path: '/combat' },
      { name: 'Equipment', path: '/equipment' },
    ],
    [
      { name: 'Gathering', path: '/skills/gathering' },
      { name: 'Refining', path: '/skills/refining' },
      { name: 'Manufacturing', path: '/skills/manufacturing' },
      { name: 'Travel', path: '/skills/travel' },
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
            <Route
              path="equipment"
              element={<EquipmentPanel profile={profile} />}
            />
            <Route path="combat" element={<CombatPanel profile={profile} />} />
            <Route
              path="market"
              element={<GlobalMarketPanel profile={profile} />}
            />
            <Route path="estate" element={<EstatePanel />} />
            <Route path="realm" element={<RealmPanel profile={profile} />} />
            <Route
              path="realm/market"
              element={<RealmMarketPanel profile={profile} />}
            />
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
            <Route
              path="skills/travel"
              element={<SkillPanel skillId="travel" />}
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
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
