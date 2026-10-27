import { renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ContentProvider, useContent } from './content'

const manifest = {
  version: 'version-one',
  packs: {
    skills: 'a',
    items: 'b',
    realms: 'c',
    upgrades: 'd',
    caps: 'e',
    map: 'f',
    estate_forms: 'g',
    development: 'h',
    projects: 'i',
    progression: 'j',
  },
}
const packBodies = {
  skills: { skills: [] },
  items: { items: [] },
  realms: { realms: [] },
  upgrades: { upgrades: [] },
  caps: {
    offline_hours: 12,
    inventory_slots: 30,
    order_slots: 5,
    key_listings: 2,
    belt_slots: 2,
    estate_upgrade_slots: 2,
  },
  map: { edges: [], positions: {} },
  estate_forms: { forms: [], transformations: [], relocation_classes: {} },
  development: { nodes: [], edges: [] },
  projects: { projects: [] },
  progression: { tier_thresholds: [1], tier_titles: ['Placeholder'] },
}

function wrapper({ children }: PropsWithChildren) {
  return <ContentProvider>{children}</ContentProvider>
}

function jsonResponse(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('content cache', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('fetches and stores packs when the manifest version changes', async () => {
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const path = String(input).split('/content/')[1]
      if (path === 'manifest') return Promise.resolve(jsonResponse(manifest))
      return Promise.resolve(
        jsonResponse(packBodies[path as keyof typeof packBodies]),
      )
    })
    vi.stubGlobal('fetch', fetchMock)

    const { result } = renderHook(() => useContent(), { wrapper })
    await waitFor(() => expect(result.current.status).toBe('ready'))

    expect(fetchMock).toHaveBeenCalledTimes(11)
    expect(result.current.content?.version).toBe(manifest.version)
    expect(localStorage.getItem('yaisg:content:manifest')).toContain(
      manifest.version,
    )
  })

  it('reuses version-keyed packs after checking an unchanged manifest', async () => {
    localStorage.setItem('yaisg:content:manifest', JSON.stringify(manifest))
    for (const [pack, value] of Object.entries(packBodies)) {
      localStorage.setItem(
        `yaisg:content:${manifest.version}:${pack}`,
        JSON.stringify(value),
      )
    }
    const fetchMock = vi.fn(() => Promise.resolve(jsonResponse(manifest)))
    vi.stubGlobal('fetch', fetchMock)

    const { result } = renderHook(() => useContent(), { wrapper })
    await waitFor(() => expect(result.current.status).toBe('ready'))

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(result.current.content?.caps.offline_hours).toBe(12)
  })

  it('keeps fetched content usable when localStorage writes fail', async () => {
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const path = String(input).split('/content/')[1]
      if (path === 'manifest') return Promise.resolve(jsonResponse(manifest))
      return Promise.resolve(
        jsonResponse(packBodies[path as keyof typeof packBodies]),
      )
    })
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('Quota exceeded', 'QuotaExceededError')
    })

    const { result } = renderHook(() => useContent(), { wrapper })
    await waitFor(() => expect(result.current.status).toBe('ready'))

    expect(result.current.content?.version).toBe(manifest.version)
    expect(fetchMock).toHaveBeenCalledTimes(11)
  })

  it('prunes stale content versions without touching unrelated storage', async () => {
    localStorage.setItem(
      'yaisg:content:manifest',
      JSON.stringify({ ...manifest, version: 'old-version' }),
    )
    localStorage.setItem('yaisg:content:old-version:skills', '{}')
    localStorage.setItem('unrelated-setting', 'keep-me')
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const path = String(input).split('/content/')[1]
      if (path === 'manifest') return Promise.resolve(jsonResponse(manifest))
      return Promise.resolve(
        jsonResponse(packBodies[path as keyof typeof packBodies]),
      )
    })
    vi.stubGlobal('fetch', fetchMock)

    const { result } = renderHook(() => useContent(), { wrapper })
    await waitFor(() => expect(result.current.status).toBe('ready'))

    expect(localStorage.getItem('yaisg:content:old-version:skills')).toBeNull()
    expect(localStorage.getItem('unrelated-setting')).toBe('keep-me')
    expect(
      localStorage.getItem(`yaisg:content:${manifest.version}:skills`),
    ).not.toBeNull()
  })
})
