import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { useDevelopmentAction } from './development'

function GateAction({ path }: { path: string }) {
  const action = useDevelopmentAction()
  return (
    <>
      <button onClick={() => action.mutate({ path, body: {} })}>Submit</button>
      {action.error && <p role="alert">{action.error.message}</p>}
    </>
  )
}
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})
it.each([
  '/realms/test/projects/project/kickoff',
  '/realms/test/upgrades/upgrade/call',
])('surfaces RESERVE_SHORT from %s', async (path) => {
  vi.stubGlobal(
    'fetch',
    vi.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            error: { code: 'RESERVE_SHORT', message: 'Realm stock is short' },
          }),
          { status: 409 },
        ),
      ),
    ),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <GateAction path={path} />
    </QueryClientProvider>,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Submit' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Realm stock is short (RESERVE_SHORT)',
  )
})
