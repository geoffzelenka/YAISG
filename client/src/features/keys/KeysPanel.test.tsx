import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { KeyDetails } from './KeysPanel'
import type { KeyInstance } from '../../api/keys'
afterEach(cleanup)
vi.mock('../../api/content', () => ({
  useContent: () => ({ status: 'loading' }),
}))
it.each(['active', 'deprecated', 'invalid', 'depleted'])(
  'shows %s key state and retained provenance',
  (state) => {
    render(
      <KeyDetails
        value={
          {
            state,
            bound_at: 'now',
            discovered_by_name: 'Discoverer',
            realm_id: 'realm',
            uses_remaining: 2,
            uses_total: 7,
            payload: { action: { name: 'Rolled resource' } },
          } as KeyInstance
        }
      />,
    )
    expect(screen.getByRole('status')).toHaveTextContent(state)
    expect(screen.getByText(/Discovered by Discoverer/)).toBeInTheDocument()
    expect(screen.getByText('Uses: 2 / 7')).toBeInTheDocument()
    expect(screen.getByText(/Bound/)).toBeInTheDocument()
    expect(!!screen.queryByText(/Deprecated: realm transition pending/)).toBe(
      state === 'deprecated',
    )
  },
)
