import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { CharacterProfile } from '../../api/characters'
import { useContent } from '../../api/content'
import { ApiError, confirmAccountUpgrade, guestSession } from '../../api/http'
import { keyRequest } from '../../api/keys'
import { TravelForm } from '../realm/TravelForm'

export function TutorialBanner({ profile }: { profile: CharacterProfile }) {
  const content = useContent()
  const client = useQueryClient()
  const [destination, setDestination] = useState('')
  const [upgradeRequired, setUpgradeRequired] = useState(false)
  const [accountSaved, setAccountSaved] = useState(false)
  const upgrade = useMutation({
    mutationFn: (credentials: { email: string; password: string }) =>
      accountSaved ? confirmAccountUpgrade() : guestSession(credentials),
    onError: (error) => {
      if (
        error instanceof ApiError &&
        error.code === 'UPGRADE_CONFIRMATION_FAILED'
      )
        setAccountSaved(true)
    },
    onSuccess: async () => {
      setUpgradeRequired(false)
      depart.reset()
      await client.invalidateQueries({ queryKey: ['players'] })
    },
  })
  const depart = useMutation({
    mutationFn: () =>
      keyRequest('/tutorial/depart', 'POST', {
        destination_realm_id: destination,
      }),
    onSuccess: async () => {
      await client.invalidateQueries()
      window.dispatchEvent(new Event('yaisg:action-changed'))
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code === 'ACCOUNT_REQUIRED')
        setUpgradeRequired(true)
    },
  })
  if (!profile.character.tutorial_step) return null
  if (content.status !== 'ready') return <p>Loading tutorial guidance…</p>
  const tutorial = content.content.tutorial
  const hint = tutorial.steps.find(
    (step) => step.id === profile.character.tutorial_step,
  )
  const realms = content.content.realms.realms
  return (
    <aside
      className="mb-6 rounded border border-emerald-700 p-4"
      aria-label="Tutorial"
    >
      <p role="status">{hint?.hint}</p>
      <TravelForm
        key={profile.character.current_realm_id}
        initialMode="relocate"
        profile={profile}
        nodes={[tutorial.realm_1, tutorial.realm_2]
          .map((id) => ({
            realm_id: id,
            name: realms.find((realm) => realm.id === id)?.name ?? id,
          }))
          .filter(
            (node) =>
              !profile.character.current_realm_id.startsWith(
                `${node.realm_id}:`,
              ),
          )}
      />
      <form
        onSubmit={(event) => {
          event.preventDefault()
          depart.mutate()
        }}
      >
        <label>
          World destination
          <select
            className="auth-input"
            required
            value={destination}
            onChange={(event) => setDestination(event.target.value)}
          >
            <option value="">Choose a destination</option>
            {tutorial.arrival_realms.map((id) => (
              <option key={id} value={id}>
                {realms.find((realm) => realm.id === id)?.name ?? id}
              </option>
            ))}
          </select>
        </label>
        <button
          className="primary-button"
          disabled={depart.isPending || upgradeRequired}
        >
          Depart Tutorial Island
        </button>
      </form>
      {depart.error && <p role="alert">{depart.error.message}</p>}
      {upgradeRequired && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            const data = new FormData(event.currentTarget)
            upgrade.mutate({
              email: String(data.get('email')),
              password: String(data.get('password')),
            })
          }}
        >
          <p>Save your guest character with an account before departure.</p>
          <label>
            Email
            <input
              className="auth-input"
              name="email"
              type="email"
              required={!accountSaved}
              disabled={accountSaved}
            />
          </label>
          <label>
            Password
            <input
              className="auth-input"
              name="password"
              type="password"
              minLength={10}
              required={!accountSaved}
              disabled={accountSaved}
            />
          </label>
          <button className="primary-button" disabled={upgrade.isPending}>
            {accountSaved ? 'Confirm saved account' : 'Upgrade account'}
          </button>
          {upgrade.error && <p role="alert">{upgrade.error.message}</p>}
        </form>
      )}
    </aside>
  )
}
