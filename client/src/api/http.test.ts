import { afterEach, expect, test, vi } from 'vitest'

import {
  gameRequest,
  readApiError,
  setAccessToken,
  setAuthenticationLostHandler,
} from './http'

afterEach(() => {
  setAccessToken(null)
  setAuthenticationLostHandler(() => undefined)
  vi.restoreAllMocks()
})

test('refreshes once after a 401 and retries with the new token', async () => {
  const fetchMock = vi
    .spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(new Response(null, { status: 401 }))
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ access_token: 'refreshed-token' }), {
        status: 200,
      }),
    )
    .mockResolvedValueOnce(new Response('{}', { status: 200 }))
  setAccessToken('expired-token')

  const response = await gameRequest('/players/me')

  expect(response.status).toBe(200)
  expect(fetchMock).toHaveBeenCalledTimes(3)
  expect(fetchMock.mock.calls[1][0]).toContain('/auth/refresh')
  const retryInit = fetchMock.mock.calls[2][1]
  expect(new Headers(retryInit?.headers).get('Authorization')).toBe(
    'Bearer refreshed-token',
  )
})

test('reports authentication loss when the retry is still unauthorized', async () => {
  vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(new Response(null, { status: 401 }))
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ access_token: 'refreshed-token' }), {
        status: 200,
      }),
    )
    .mockResolvedValueOnce(new Response(null, { status: 401 }))
  const authenticationLost = vi.fn()
  setAccessToken('expired-token')
  setAuthenticationLostHandler(authenticationLost)

  const response = await gameRequest('/players/me')

  expect(response.status).toBe(401)
  expect(authenticationLost).toHaveBeenCalledOnce()
})

test('reads structured API errors', async () => {
  const error = await readApiError(
    new Response(
      JSON.stringify({
        error: { code: 'MISSING_INPUTS', message: 'Missing inputs' },
      }),
      { status: 409, headers: { 'Content-Type': 'application/json' } },
    ),
    'Fallback',
  )

  expect(error).toEqual({ code: 'MISSING_INPUTS', message: 'Missing inputs' })
})

test('falls back cleanly for non-JSON API errors', async () => {
  const error = await readApiError(
    new Response('<html>Bad gateway</html>', {
      status: 502,
      statusText: 'Bad Gateway',
      headers: { 'Content-Type': 'text/html' },
    }),
    'Request failed (502)',
  )

  expect(error).toEqual({ message: 'Bad Gateway' })
})
