import { type FormEvent, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from './AuthProvider'

export function AuthForm({ mode }: { mode: 'login' | 'register' }) {
  const auth = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (auth.state === 'loading') {
    return (
      <p className="grid min-h-screen place-items-center">Restoring session…</p>
    )
  }
  if (auth.state === 'authenticated') {
    const destination =
      (location.state as { from?: string } | null)?.from ?? '/'
    return <Navigate to={destination} replace />
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    const form = new FormData(event.currentTarget)
    try {
      await auth[mode](String(form.get('email')), String(form.get('password')))
      navigate('/', { replace: true })
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : 'Authentication failed',
      )
    } finally {
      setSubmitting(false)
    }
  }

  const isLogin = mode === 'login'
  return (
    <main className="grid min-h-screen place-items-center px-6">
      <form
        className="w-full max-w-sm rounded-xl border border-slate-700 bg-slate-900 p-8 shadow-xl"
        onSubmit={(event) => void submit(event)}
      >
        <p className="text-sm font-semibold uppercase tracking-widest text-emerald-400">
          YAISG
        </p>
        <h1 className="mt-2 text-3xl font-bold">
          {isLogin ? 'Welcome back' : 'Create account'}
        </h1>
        <label className="mt-6 block text-sm" htmlFor="email">
          Email
        </label>
        <input
          className="auth-input"
          id="email"
          name="email"
          type="email"
          required
        />
        <label className="mt-4 block text-sm" htmlFor="password">
          Password
        </label>
        <input
          className="auth-input"
          id="password"
          name="password"
          type="password"
          minLength={10}
          required
        />
        {error !== null && <p className="mt-4 text-sm text-red-300">{error}</p>}
        <button className="primary-button mt-6 w-full" disabled={submitting}>
          {submitting ? 'Please wait…' : isLogin ? 'Log in' : 'Register'}
        </button>
        <button
          type="button"
          className="secondary-button mt-4"
          disabled={submitting}
          onClick={() => {
            setSubmitting(true)
            setError(null)
            void auth
              .guest()
              .then(() => navigate('/', { replace: true }))
              .catch((caught: unknown) =>
                setError(
                  caught instanceof Error ? caught.message : 'Unable to play',
                ),
              )
              .finally(() => setSubmitting(false))
          }}
        >
          Play now
        </button>
        <p className="mt-5 text-sm text-slate-400">
          {isLogin ? 'Need an account?' : 'Already registered?'}{' '}
          <Link
            className="text-emerald-400 hover:underline"
            to={isLogin ? '/register' : '/login'}
          >
            {isLogin ? 'Register' : 'Log in'}
          </Link>
        </p>
      </form>
    </main>
  )
}
