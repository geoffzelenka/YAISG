import { useQueryClient } from '@tanstack/react-query'
import {
  createContext,
  type PropsWithChildren,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  authenticate,
  guestSession,
  logout as requestLogout,
  refreshAccessToken,
  setAccessToken,
  setAuthenticationLostHandler,
} from '../../api/http'

type AuthState = 'loading' | 'authenticated' | 'unauthenticated'

type AuthContextValue = {
  state: AuthState
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  guest: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: PropsWithChildren) {
  const client = useQueryClient()
  const [state, setState] = useState<AuthState>('loading')

  useEffect(() => {
    setAuthenticationLostHandler(() => setState('unauthenticated'))
    void refreshAccessToken()
      .then(() => setState('authenticated'))
      .catch(() => {
        setAccessToken(null)
        setState('unauthenticated')
      })
    return () => setAuthenticationLostHandler(() => undefined)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      state,
      login: async (email, password) => {
        await authenticate('login', email, password)
        client.clear()
        setState('authenticated')
      },
      register: async (email, password) => {
        await authenticate('register', email, password)
        client.clear()
        setState('authenticated')
      },
      guest: async () => {
        await guestSession()
        client.clear()
        setState('authenticated')
      },
      logout: async () => {
        await requestLogout()
        client.clear()
        setState('unauthenticated')
      },
    }),
    [state, client],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// The provider and hook intentionally share their private context.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
