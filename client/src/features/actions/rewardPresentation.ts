import type { Rewards } from '../../api/actions'

export function shouldShowWelcomeBack(rewards: Rewards): boolean {
  return rewards.cycles_completed > 5
}
