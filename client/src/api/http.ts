export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message)
  }
}

const authUrl = String(import.meta.env.VITE_AUTH_URL ?? 'http://localhost:8001')
const gameUrl = String(import.meta.env.VITE_GAME_URL ?? 'http://localhost:8000')

type TokenResponse = { access_token: string }
export type ApiErrorDetails = { code?: string; message: string }

let accessToken: string | null = null
let refreshRequest: Promise<string> | null = null
let onAuthenticationLost: () => void = () => undefined

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function setAuthenticationLostHandler(handler: () => void) {
  onAuthenticationLost = handler
}

export async function readApiError(
  response: Response,
  fallbackMessage: string,
): Promise<ApiErrorDetails> {
  try {
    const payload = (await response.json()) as {
      error?: { code?: unknown; message?: unknown }
    }
    return {
      code:
        typeof payload.error?.code === 'string'
          ? payload.error.code
          : undefined,
      message:
        typeof payload.error?.message === 'string'
          ? payload.error.message
          : fallbackMessage,
    }
  } catch {
    return {
      message: response.statusText || fallbackMessage,
    }
  }
}

async function requestRefresh(): Promise<string> {
  const response = await fetch(`${authUrl}/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!response.ok) {
    throw new Error('Session refresh failed')
  }
  const payload = (await response.json()) as TokenResponse
  accessToken = payload.access_token
  return payload.access_token
}

export async function refreshAccessToken(): Promise<string> {
  refreshRequest ??= requestRefresh().finally(() => {
    refreshRequest = null
  })
  return refreshRequest
}

function authenticatedHeaders(init?: RequestInit): Headers {
  const headers = new Headers(init?.headers)
  if (accessToken !== null) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }
  return headers
}

export async function gameRequest(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  let response = await fetch(`${gameUrl}${path}`, {
    ...init,
    headers: authenticatedHeaders(init),
  })
  if (response.status !== 401) {
    return response
  }
  try {
    await refreshAccessToken()
  } catch {
    accessToken = null
    onAuthenticationLost()
    return response
  }
  response = await fetch(`${gameUrl}${path}`, {
    ...init,
    headers: authenticatedHeaders(init),
  })
  if (response.status === 401) {
    accessToken = null
    onAuthenticationLost()
  }
  return response
}

export async function authenticate(
  action: 'login' | 'register',
  email: string,
  password: string,
): Promise<void> {
  const response = await fetch(`${authUrl}/auth/${action}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!response.ok) {
    const error = await readApiError(response, 'Authentication failed')
    throw new Error(error.message)
  }
  const payload = (await response.json()) as TokenResponse
  setAccessToken(payload.access_token)
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${authUrl}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    })
  } finally {
    setAccessToken(null)
  }
}
