import { render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { App } from './App'

afterEach(() => {
  vi.restoreAllMocks()
})

test('shows both services as healthy', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const service = String(input).includes('8001') ? 'auth' : 'game'
    return Promise.resolve(
      new Response(JSON.stringify({ status: 'ok', service, version: 'dev' })),
    )
  })

  render(<App />)

  expect(screen.getByLabelText('Game service: loading')).toHaveClass(
    'bg-slate-500',
  )
  expect(
    screen.getByRole('heading', { name: 'Yet Another Idle Skilling Game' }),
  ).toBeInTheDocument()
  expect(await screen.findAllByText('Healthy · version dev')).toHaveLength(2)
  expect(screen.getByLabelText('Game service: healthy')).toHaveClass(
    'bg-emerald-400',
  )
})
