import {
  createContext,
  type PropsWithChildren,
  useContext,
  useEffect,
  useState,
} from 'react'

import { gameRequest } from './http'

export type ModifierType =
  | 'combat_accuracy_pct'
  | 'combat_power_pct'
  | 'combat_defense_pct'
  | 'combat_armour_pct'
  | 'combat_hp_pct'
  | 'journey_speed_pct'
  | 'supply_reduction_pct'
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
  combatant_id?: string | null
  location?: string | null
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
export type Combatant = {
  id: string
  name: string
  tier: number
  style: 'melee' | 'ranged' | 'magic'
  max_hp: number
  accuracy: number
  power: number
  defense: number
  armour: number
  attack_interval_ms: number
  respawn_ms: number
  weak_to: string[]
  resistant_to: string[]
  xp_pool_offense: number
  xp_pool_defense: number
  defense_xp_per_damage: number
  drops: Action['outputs']
}
export type EquipmentSlot =
  | 'head'
  | 'chest'
  | 'gloves'
  | 'legs'
  | 'feet'
  | 'neck'
  | 'left_arm'
  | 'right_arm'
  | 'left_ring'
  | 'right_ring'
  | 'belt'
  | 'cape'
  | 'right_hand'
  | 'left_hand'
  | 'utility'
export type Trigger = { hp_below_pct: number } | { buff_missing: true }
export type Item = {
  equip?: {
    slot: EquipmentSlot | 'ring' | 'arm'
    two_handed: boolean
    requires: Record<string, number>
    modifiers: Modifier[]
    cap_bonuses: Partial<Record<keyof Caps | 'estate_upgrade_slots', number>>
    weapon: {
      style: 'melee' | 'ranged' | 'magic'
      attack_interval_ms: number
      power: number
      accuracy: number
      damage_type: string
    } | null
    armour: { armour: number; max_hp: number } | null
    tool_class: string | null
    belt_slots: number | null
  } | null
  consumable?: {
    heal: number | null
    buff: { modifiers: Modifier[]; duration_ms: number } | null
    utility_for: 'melee' | 'ranged' | 'magic' | null
  } | null
  id: string
  name: string
  tier: number
  classes: string[]
  warehouse_cap?: number | null
  reference_price: number
  instanced?: boolean
  bullion: boolean
  spoilage_pct_per_day: number
  stack_limit: number
  tags: string[]
}
export type Realm = {
  id: string
  name: string
  starting_node_id: string
  isolated: boolean
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
}

export type CapBonus = {
  cap: keyof Caps | 'estate_upgrade_slots'
  value: number
}

export type EstateForm = {
  id: string
  name: string
  tags: string[]
  requires_realm_tags: string[]
  tier: number
  upgrade_slots: number
  build_cost: {
    gold: number
    goods: { selector: Selector; quantity: number }[]
  }
  transforms_to: string[]
  regresses_to: string | null
  upkeep: { selector: Selector; per_day: number }[]
  production: { item_id: string; per_day: number }[]
  mobility: 'mobile' | 'fixed'
  travel_profile: TravelProfile | null
  cap_bonuses: CapBonus[]
  modifiers: Modifier[]
}
export type DevelopmentNode = {
  tier: number
  id: string
  inherent_tags: string[]
  actions: string[]
  realm_type: string
  name: string
  modifiers: Modifier[]
  cap_bonuses: { cap: keyof Caps; value: number }[]
  projects: string[]
  carried_tags: string[]
  upkeep: { selector: Selector; per_day: number }[]
  upgrades: {
    id: string
    to_node: string
    kind: 'tier_up' | 'morph'
    required_tags: string[]
    fee_gold: number
  }[]
  regression: { to_node: string } | null
  reserve_days?: number | null
  cap_days?: number | null
  margin_pct?: number | null
}
export type Project = {
  id: string
  name: string
  grants_tag: string
  kickoff: {
    gold: number
    goods: Action['inputs']
    who: 'residents' | 'anyone'
  }
  cost: Action['inputs']
  build_seconds: number
  realm_completion_days: number
  requires_tags: string[]
  repeatable: false
}
export type TravelProfile = {
  time_mult: number
  supply_mult: number
  terrains: ('land' | 'water')[]
}

export type MapEdge = {
  id: string
  a: string
  b: string
  terrain: 'land' | 'water'
  base_time_s: number
  supplies: Action['inputs']
  min_travel_level: number
  base_loss_pct: number
  one_way: boolean
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
  tutorial: {
    realm_1: string
    realm_2: string
    arrival_realms: string[]
    raft_site_project: string
    raft_form: string
    steps: {
      id: string
      hint: string
      done_when: { kind: string; id: string; quantity?: number }
    }[]
  }

  tags: { tags: Tag[] }
  economy: {
    caravan?: {
      pass_every_ticks: number
      fee_pct_per_hour: number
      fee_burn_pct: number
      time_mult: number
      capacity_value_per_pass: number
    }
    reserve_days: number
    cap_days: number
    market?: {
      tax_pct?: number
      tax_burn_pct?: number
      order_days?: number
      retention_days?: number
      lifecycle_interval_seconds?: number
      f: number
      c: number
      k: number
      m: number
      band_days: [number, number, number, number]
      band_hysteresis_pct: number
    }
    warehouse_value_cap: number
    coinage_multiple: number
    vote: {
      min_stock_days: number
      duration_hours: number
      fail_cooldown_hours: number
    }
    decay: { faltering_factor: number }
    transition: { duration_days: number }
    project: {
      idle_grace_days: number
      erosion_pct_per_day: number
      fail_cooldown_hours: number
    }
    tick: { per_day: number; max_catchup: number }
    estate: { sale_markup_pct: number }
  }
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
  }
  development: { nodes: DevelopmentNode[] }
  progression: {
    combat?: {
      base_hp: number
      hp_per_level: number
      regen_per_min: number
      min_engage_hp_pct: number
      base_hit: number
      hit_per_level: number
      tier_multiplier: number
      min_hit_chance: number
      max_hit_chance: number
      weakness_multiplier: number
      resistance_multiplier: number
      armour_k: number
      taken_to_defense_pct: number
      max_cycles_per_resolve: number
      standard_gear: Partial<Record<EquipmentSlot, string>>
      unarmed: NonNullable<NonNullable<Item['equip']>['weapon']>
    }
    stances?: Record<string, { style: number; accuracy: number }>
    default_stance?: string
    combat_effectiveness?: number[]
    basic_mobile_form: string
    visit_profile: TravelProfile
    travel_xp_per_second: number
    tier_benefits: {
      exploration?: {
        cycle_speed_pct: number
        keys_per_discovery_bonus: number
        rarity_weight_shift: number
      }[]
      travel: { journey_speed_pct: number; supply_reduction_pct: number }[]
    }
    lint: { g: number; tolerance_pct: number }
    tier_thresholds: number[]
    tier_titles: string[]
    min_factor: number
    min_cycle_ms: number
    xp_bonus_cap_pct: number
    proficiency: Record<Skill['category'], number[]>
    taper: Record<Skill['category'], number[]>
  }
  exploration: {
    templates: {
      id: string
      name: string
      flavour: string
      rarity: number
      kind: 'gather' | 'combat'
      gather:
        | (Pick<
            Action,
            | 'skill_id'
            | 'tier'
            | 'unlock_level'
            | 'base_cycle_ms'
            | 'outputs'
            | 'xp'
          > & { tool_class: string | null })
        | null
      combat: { combatant_id: string } | null
      uses: { min: number; max: number }
      keys: { min: number; max: number }
      requires_realm_tags: string[]
    }[]
    actions: (Action & {
      discovery_chance: number
      table: { template_id: string; weight: number }[]
      consumable_effects: {
        item_id: string
        chance_pct: number | null
        weight_shift: number | null
      }[]
    })[]
  }
  combatants: { combatants: Combatant[] }
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
  'tutorial',
  'exploration',
  'combatants',
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
