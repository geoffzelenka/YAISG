import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, it, vi } from 'vitest'
import { AuthProvider } from './AuthProvider'
import { App } from '../../App'
import { setAccessToken } from '../../api/http'
it('routes Play now to character creation through an authenticated guest session', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((url) =>
    Promise.resolve(
      String(url).endsWith('/auth/refresh')
        ? new Response(null, { status: 401 })
        : String(url).endsWith('/characters/me')
          ? new Response(
              JSON.stringify({
                error: {
                  code: 'NO_CHARACTER',
                  message: 'Create a character',
                },
              }),
              { status: 404 },
            )
          : new Response(JSON.stringify({ access_token: 'guest-token' })),
    ),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  fireEvent.click(await screen.findByText('Play now'))
  await screen.findByText('Create your character')
  expect(
    fetchMock.mock.calls.some(
      ([url, init]) =>
        String(url).endsWith('/auth/guest') &&
        init?.method === 'POST' &&
        init.credentials === 'include',
    ),
  ).toBe(true)
  setAccessToken(null)
  vi.restoreAllMocks()
})
