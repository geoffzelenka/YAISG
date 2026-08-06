import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { useContent } from '../../api/content'
import { useEstate } from '../../api/estates'
import { Countdown } from './Countdown'

export function PendingRelocationBanner() {
  const client = useQueryClient()
  const content = useContent()
  const estate = useEstate()
  const expire = useCallback(() => {
    void client.invalidateQueries({
      queryKey: ['characters', 'me'],
      exact: true,
    })
    void client.invalidateQueries({ queryKey: ['estates', 'me'] })
    void client.invalidateQueries({
      queryKey: ['characters', 'me', 'actions', 'available'],
    })
  }, [client])
  if (
    !estate.data?.relocating_to_realm_id ||
    !estate.data.relocation_completes_at
  )
    return null
  const destination =
    content.status === 'ready'
      ? content.content.realms.realms.find(
          (realm) => realm.id === estate.data.relocating_to_realm_id,
        )?.name
      : undefined
  return (
    <aside
      className="border-t border-amber-500 bg-amber-950 px-6 py-3"
      role="status"
    >
      <strong>
        Relocating to {destination ?? estate.data.relocating_to_realm_id}
      </strong>{' '}
      · arriving in{' '}
      <Countdown
        completesAt={estate.data.relocation_completes_at}
        onExpire={expire}
      />
    </aside>
  )
}
