import {
  createContext,
  type PropsWithChildren,
  useContext,
  useEffect,
  useState,
} from 'react'

import { gameRequest } from './http'

export type ModifierType =
  | 'cycle_speed_pct'
  | 'xp_pct'
  | 'extra_drop_chance_pct'

export type ItemQuantity = { item_id: string; qty: number }
export type Modifier = {
  type: ModifierType
  value: number
  category?: Skill['category'] | null
  skill_id?: string | null
}
export type Selector =
  | { item: string; class?: never; tier?: never }
  | { class: string; tier?: number; item?: never }
export type Action = {
  id: string
  name: string
  skill_id: string
  unlock_level: number
  tier: number
  base_cycle_ms: number
  inputs: { selector: Selector; quantity: number }[]
  xp: number
  outputs: {
    item_id: string
    quantity_min: number
    quantity_max: number
    chance: number
    off_tier: boolean
  }[]
  requires: {
    facility?: string | null
    realm_tags: string[]
    skill_levels: Record<string, number>
    tool_class?: string | null
  }
  resolver: 'uniform' | 'combat' | 'travel'
  off_curve: string | null
}
export type Skill = {
  id: string
  name: string
  category:
    | 'gathering'
    | 'refining'
    | 'manufacturing'
    | 'combat'
    | 'exploration'
    | 'travel'
  actions: Action[]
}
export type Item = {
  id: string
  name: string
  tier: number
  classes: string[]
  reference_price: number
  bullion: boolean
  spoilage_pct_per_day: number
  stack_limit: number
  tags: string[]
}
export type Realm = {
  id: string
  name: string
  starting_node_id: string
}
export type EstateUpgrade = {
  id: string
  name: string
  cost: ItemQuantity[]
  modifiers: Modifier[]
  cap_bonuses: {
    cap:
      | 'offline_hours'
      | 'inventory_slots'
      | 'order_slots'
      | 'key_listings'
      | 'belt_slots'
      | 'estate_upgrade_slots'
    value: number
  }[]
  requires_realm_tags: string[]
  tags: string[]
}
export type Caps = {
  offline_hours: number
  inventory_slots: number
  order_slots: number
  key_listings: number
  belt_slots: number
  estate_upgrade_slots: number
}

export type EstateForm = {
  id: string
  name: string
  tags: string[]
  requires_realm_tags: string[]
  specialty_tags: string[]
  relocation_class: string
  base_caps: Partial<Caps>
  modifiers: Modifier[]
}
export type FormTransformation = {
  from: string
  to: string
  cost: ItemQuantity[]
}
export type DevelopmentNode = {
  id: string
  inherent_tags: string[]
  actions: string[]
  archetype: string
  name: string
  modifiers: Modifier[]
  cap_bonuses: { cap: keyof Caps; value: number }[]
  projects: string[]
}
export type DevelopmentEdge = {
  id: string
  from: string
  to: string
  progress_target: number
  kind: 'development' | 'regression'
  transition_ms?: number
}
export type Project = {
  id: string
  name: string
  targets: ItemQuantity[]
  awards: { edge_id: string; progress: number }[]
}
export type MapEdge = {
  realms: [string, string]
  cost: { gold: number; items: ItemQuantity[]; time_ms: number }
}

export type Tag = {
  id: string
  name: string
  kind: 'facility' | 'bonus' | 'malus' | 'access'
  modifiers: Modifier[]
  cap_bonuses: Partial<Caps>
  upkeep: { selector: Selector; per_day: number }[]
  effects: {
    market_access: boolean
    caravan_access: boolean
    mint: { value_per_day: number } | null
    edge_loss_reduction_pct: number
    reserve_days_delta: number
  }
}

type ContentPacks = {
  tags: { tags: Tag[] }
  economy: { decay: { faltering_factor: number } }
  skills: { skills: Skill[] }
  items: { items: Item[] }
  realms: { realms: Realm[] }
  upgrades: { upgrades: EstateUpgrade[] }
  caps: Caps
  map: {
    edges: MapEdge[]
    positions: Record<string, { x: number; y: number }>
  }
  estate_forms: {
    forms: EstateForm[]
    transformations: FormTransformation[]
  }
  development: { nodes: DevelopmentNode[]; edges: DevelopmentEdge[] }
  progression: {
    lint: { g: number; tolerance_pct: number }
    tier_thresholds: number[]
    tier_titles: string[]
    min_factor: number
    min_cycle_ms: number
    xp_bonus_cap_pct: number
    proficiency: Record<Skill['category'], number[]>
    taper: Record<Skill['category'], number[]>
  }
  projects: { projects: Project[] }
}
type PackName = keyof ContentPacks
type Manifest = { version: string; packs: Record<PackName, string> }
export type Content = ContentPacks & { version: string }
type ContentState =
  | { status: 'loading'; content: null; error: null }
  | { status: 'ready'; content: Content; error: null }
  | { status: 'error'; content: null; error: Error }

const PACKS: PackName[] = [
  'skills',
  'items',
  'realms',
  'upgrades',
  'caps',
  'map',
  'estate_forms',
  'development',
  'projects',
  'progression',
  'tags',
  'economy',
]
const MANIFEST_KEY = 'yaisg:content:manifest'
const PACK_KEY_PREFIX = 'yaisg:content:'
const ContentContext = createContext<ContentState | null>(null)

function packKey(version: string, pack: PackName): string {
  return `${PACK_KEY_PREFIX}${version}:${pack}`
}

function writeCache(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Content remains usable when storage is unavailable or over quota.
  }
}

function pruneStalePacks(version: string): void {
  const currentPrefix = `${PACK_KEY_PREFIX}${version}:`
  try {
    const staleKeys: string[] = []
    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index)
      if (
        key !== null &&
        key !== MANIFEST_KEY &&
        key.startsWith(PACK_KEY_PREFIX) &&
        !key.startsWith(currentPrefix)
      ) {
        staleKeys.push(key)
      }
    }
    for (const key of staleKeys) localStorage.removeItem(key)
  } catch {
    // Cache cleanup is best-effort for restricted browser storage.
  }
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await gameRequest(path)
  if (!response.ok) {
    throw new Error(`Content request failed (${response.status})`)
  }
  return (await response.json()) as T
}

function readCached(manifest: Manifest): ContentPacks | null {
  const result: Partial<ContentPacks> = {}
  try {
    for (const pack of PACKS) {
      const value = localStorage.getItem(packKey(manifest.version, pack))
      if (value === null) return null
      const parsed = JSON.parse(value) as unknown
      const cache = result as Record<string, unknown>
      cache[pack] = parsed
    }
    return result as ContentPacks
  } catch {
    return null
  }
}

async function loadContent(): Promise<Content> {
  const manifest = await fetchJson<Manifest>('/content/manifest')
  let priorManifest: string | null = null
  try {
    priorManifest = localStorage.getItem(MANIFEST_KEY)
  } catch {
    // Continue without a cache when browser storage is unavailable.
  }
  if (priorManifest !== null) {
    try {
      const prior = JSON.parse(priorManifest) as Manifest
      if (prior.version === manifest.version) {
        const cached = readCached(manifest)
        if (cached !== null) {
          pruneStalePacks(manifest.version)
          return { ...cached, version: manifest.version }
        }
      }
    } catch {
      // A corrupt cache is safely replaced from the server below.
    }
  }

  const entries = await Promise.all(
    PACKS.map(async (pack) => {
      const value = await fetchJson<ContentPacks[typeof pack]>(
        `/content/${pack}`,
      )
      writeCache(packKey(manifest.version, pack), value)
      return [pack, value] as const
    }),
  )
  const packs = Object.fromEntries(entries) as ContentPacks
  writeCache(MANIFEST_KEY, manifest)
  pruneStalePacks(manifest.version)
  return { ...packs, version: manifest.version }
}

export function ContentProvider({ children }: PropsWithChildren) {
  const [state, setState] = useState<ContentState>({
    status: 'loading',
    content: null,
    error: null,
  })

  useEffect(() => {
    let active = true
    void loadContent().then(
      (content) => {
        if (active) setState({ status: 'ready', content, error: null })
      },
      (error: unknown) => {
        if (active) {
          setState({
            status: 'error',
            content: null,
            error:
              error instanceof Error ? error : new Error('Content load failed'),
          })
        }
      },
    )
    return () => {
      active = false
    }
  }, [])

  return (
    <ContentContext.Provider value={state}>{children}</ContentContext.Provider>
  )
}

// The provider and hook intentionally share their private context.
// eslint-disable-next-line react-refresh/only-export-components
export function useContent(): ContentState {
  const value = useContext(ContentContext)
  if (value === null) {
    throw new Error('useContent must be used within ContentProvider')
  }
  return value
}
