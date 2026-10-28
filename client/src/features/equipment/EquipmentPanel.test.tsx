import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type { CharacterProfile } from '../../api/characters'
import type { Item } from '../../api/content'
import { EquipmentPanel, StackForm } from './EquipmentPanel'

vi.mock('../../api/content', () => ({
  useContent: () => ({
    status: 'ready',
    content: {
      items: {
        items: [
          { id: 'food', name: 'Food', consumable: { heal: 10 } },
          { id: 'ammo', name: 'Ammo', consumable: { utility_for: 'ranged' } },
          {
            id: 'belt',
            name: 'Belt',
            equip: { slot: 'belt', belt_slots: 2, requires: {} },
          },
          {
            id: 'staff',
            name: 'Staff',
            equip: {
              slot: 'right_hand',
              two_handed: true,
              requires: { magic: 4 },
            },
          },
          {
            id: 'shield',
            name: 'Shield',
            equip: { slot: 'left_hand', requires: {} },
          },
        ],
      },
      skills: { skills: [{ actions: [{ id: 'fight', resolver: 'combat' }] }] },
    },
  }),
}))
vi.mock('../../api/http', async (original) => ({
  ...(await original<typeof import('../../api/http')>()),
  gameRequest: (path: string, init?: RequestInit) => fetch(path, init),
}))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})
function setup(
  twoHanded: boolean,
  fighting = false,
  overrides: Partial<CharacterProfile> = {},
) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  client.setQueryData(['characters', 'me', 'action'], {
    active: fighting ? { action_id: 'fight' } : null,
  })
  const fetcher = vi.fn(async () => {
    await Promise.resolve()
    return Response.json({
      items: [
        { item_id: 'staff', quantity: 1 },
        { item_id: 'shield', quantity: 1 },
        { item_id: 'ammo', quantity: 10 },
        { item_id: 'food', quantity: 10 },
      ],
    })
  })
  vi.stubGlobal('fetch', fetcher)
  const invalidate = vi.spyOn(client, 'invalidateQueries')
  const profile = {
    equipment: twoHanded
      ? { right_hand: { item_id: 'staff', quantity: 1 } }
      : {},
    caps: { belt_slots: { effective: 1 } },
    skills: [{ id: 'magic', name: 'Magic', level: 4 }],
    ...overrides,
  } as unknown as CharacterProfile
  const view = render(
    <QueryClientProvider client={client}>
      <EquipmentPanel profile={profile} />
    </QueryClientProvider>,
  )
  return { client, fetcher, invalidate, ...view }
}
it('blocks the left hand for a two-handed item and permits removing the right hand', async () => {
  setup(true)
  expect(
    await screen.findByText('Blocked by two-handed right-hand equipment'),
  ).toBeInTheDocument()
  await waitFor(() =>
    expect(screen.getByText('Unequip right hand')).toBeEnabled(),
  )
  expect(screen.getByText('Equip Shield in left hand')).toBeDisabled()
  expect(
    screen.getAllByText('Requirements: Magic 4 (current 4; met)').length,
  ).toBeGreaterThan(0)
})
it('equips a two-handed item using the concrete right-hand slot and refreshes views', async () => {
  const { fetcher } = setup(false)
  const button = await screen.findByText('Equip Staff in right hand')
  await waitFor(() => expect(button).toBeEnabled())
  fireEvent.click(button)
  await waitFor(() =>
    expect(fetcher).toHaveBeenCalledWith(
      '/equipment/equip',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ slot: 'right_hand', item_id: 'staff' }),
      }),
    ),
  )
})
it('disables permanent gear, utility and belt controls during combat with a reason', async () => {
  const { container } = setup(false, true)
  await screen.findByText('Equip Staff in right hand')
  expect(screen.getByText(/Stop combat to change/)).toBeInTheDocument()
  for (const fieldset of container.querySelectorAll('fieldset'))
    expect(fieldset).toBeDisabled()
})
it('submits healing thresholds and buff-missing belt triggers and clears stacks', () => {
  const onSave = vi.fn()
  const items = [
    { id: 'food', name: 'Food', consumable: { heal: 10 } },
    { id: 'buff', name: 'Buff', consumable: { buff: { duration_ms: 100 } } },
  ] as unknown as Item[]
  render(
    <StackForm
      items={items}
      current={{ item_id: 'food', quantity: 3, trigger: { hp_below_pct: 25 } }}
      belt
      disabled={false}
      onSave={onSave}
    />,
  )
  fireEvent.change(screen.getByLabelText('HP below (%)'), {
    target: { value: '35' },
  })
  fireEvent.click(screen.getByText('Assign stack'))
  expect(onSave).toHaveBeenLastCalledWith({
    item_id: 'food',
    quantity: 3,
    trigger: { hp_below_pct: 35 },
  })
  fireEvent.change(screen.getByLabelText('Item'), { target: { value: 'buff' } })
  expect(screen.queryByLabelText('HP below (%)')).not.toBeInTheDocument()
  fireEvent.click(screen.getByText('Assign stack'))
  expect(onSave).toHaveBeenLastCalledWith({
    item_id: 'buff',
    quantity: 3,
    trigger: { buff_missing: true },
  })
  fireEvent.click(screen.getByText('Return stack'))
  expect(onSave).toHaveBeenLastCalledWith({
    item_id: null,
    quantity: 0,
    trigger: null,
  })
  expect(
    within(screen.getByRole('combobox')).getAllByRole('option'),
  ).toHaveLength(3)
})

it('assigns utility through its PUT endpoint and refreshes character holders', async () => {
  const { fetcher, invalidate } = setup(false)
  await waitFor(() => expect(screen.getAllByLabelText('Item')[0]).toBeEnabled())
  fireEvent.change(screen.getAllByLabelText('Item')[0], {
    target: { value: 'ammo' },
  })
  fireEvent.change(screen.getAllByLabelText('Quantity')[0], {
    target: { value: '5' },
  })
  fireEvent.click(screen.getAllByText('Assign stack')[0])
  await waitFor(() =>
    expect(fetcher).toHaveBeenCalledWith(
      '/equipment/utility',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ item_id: 'ammo', quantity: 5 }),
      }),
    ),
  )
  await waitFor(() =>
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['characters', 'me'] }),
  )
})
it('adds belt positions to the resolved cap and allows returning an unavailable position', async () => {
  const { fetcher } = setup(false, false, {
    equipment: { belt: { item_id: 'belt', quantity: 1 } },
    belt: {
      5: { item_id: 'food', quantity: 2, trigger: { hp_below_pct: 40 } },
    },
  })
  expect(await screen.findByText('Belt (3 positions)')).toBeInTheDocument()
  const heading = screen.getByText('Position 6 (unavailable; return only)')
  const position = heading.parentElement!
  expect(within(position).getByText('Assign stack')).toBeDisabled()
  fireEvent.click(within(position).getByText('Return stack'))
  await waitFor(() =>
    expect(fetcher).toHaveBeenCalledWith(
      '/equipment/belt/5',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ item_id: null, quantity: 0, trigger: null }),
      }),
    ),
  )
})

it('locks equipment, belt and utility for a private combat key template', async () => {
  const { client, container } = setup(false)
  await screen.findByText('Equip Staff in right hand')
  act(() => {
    client.setQueryData(['characters', 'me', 'action'], {
      active: {
        action_id: 'private-template',
        meta: {
          key_id: 'held-instance',
          key_action: { id: 'private-template', resolver: 'combat' },
        },
      },
    })
  })
  await screen.findByText(/Stop combat to change/)
  for (const fieldset of container.querySelectorAll('fieldset'))
    expect(fieldset).toBeDisabled()
})

it.each([0, -1, 100.01, NaN, Infinity, 0.001, 100])(
  'validates healing trigger %s at submit even without native form validation',
  (threshold) => {
    const onSave = vi.fn()
    const { container } = render(
      <StackForm
        items={[{ id: 'food', name: 'Food', consumable: { heal: 10 } } as Item]}
        current={{
          item_id: 'food',
          quantity: 1,
          trigger: { hp_below_pct: threshold },
        }}
        belt
        disabled={false}
        onSave={onSave}
      />,
    )
    fireEvent.submit(container.querySelector('form')!)
    const valid =
      Number.isFinite(threshold) && threshold > 0 && threshold <= 100
    expect(onSave).toHaveBeenCalledTimes(Number(valid))
    if (valid) {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    } else {
      expect(screen.getByRole('alert')).toHaveTextContent(
        'HP threshold must be greater than 0 and at most 100.',
      )
      expect(screen.getByLabelText('HP below (%)')).toHaveAttribute(
        'aria-invalid',
        'true',
      )
    }
  },
)

it('clears the inline threshold error when a healing trigger is corrected', () => {
  const onSave = vi.fn()
  const { container } = render(
    <StackForm
      items={[{ id: 'food', name: 'Food', consumable: { heal: 10 } } as Item]}
      current={{ item_id: 'food', quantity: 1, trigger: { hp_below_pct: 0 } }}
      belt
      disabled={false}
      onSave={onSave}
    />,
  )
  expect(screen.getByRole('alert')).toHaveTextContent('HP threshold')
  fireEvent.change(screen.getByLabelText('HP below (%)'), {
    target: { value: '0.001' },
  })
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  expect(screen.getByLabelText('HP below (%)')).toHaveAttribute(
    'aria-invalid',
    'false',
  )
  fireEvent.submit(container.querySelector('form')!)
  expect(onSave).toHaveBeenCalledWith({
    item_id: 'food',
    quantity: 1,
    trigger: { hp_below_pct: 0.001 },
  })
})

it('keeps unequip and assigned stack returns disabled during combat', async () => {
  setup(true, true, {
    equipment: {
      right_hand: { item_id: 'staff', quantity: 1 },
      utility: { item_id: 'ammo', quantity: 3 },
    },
    belt: {
      0: { item_id: 'food', quantity: 2, trigger: { hp_below_pct: 50 } },
    },
  })
  expect(await screen.findByText('Unequip right hand')).toBeDisabled()
  for (const button of await screen.findAllByText('Return stack'))
    expect(button).toBeDisabled()
  expect(
    screen.getByRole('group', { name: 'Equipment doll' }),
  ).toBeInTheDocument()
  expect(screen.getByRole('group', { name: 'Position 1' })).toBeInTheDocument()
})

it('shows unmet equipment requirements with the default level for a missing skill', async () => {
  setup(false, false, { skills: [] })
  expect(
    await screen.findByText('Requirements: magic 4 (current 1; unmet)'),
  ).toBeInTheDocument()
  expect(screen.getByText('Equip Staff in right hand')).toBeDisabled()
})
