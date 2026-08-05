import { create } from 'zustand'

type ClockState = {
  now: number
  setNow: (now: number) => void
}

export const useActionClock = create<ClockState>((set) => ({
  now: Date.now(),
  setNow: (now) => set({ now }),
}))

let subscribers = 0
let clockInterval: ReturnType<typeof setInterval> | undefined

export function startActionClock(): () => void {
  subscribers += 1
  if (clockInterval === undefined) {
    useActionClock.getState().setNow(Date.now())
    clockInterval = setInterval(() => {
      useActionClock.getState().setNow(Date.now())
    }, 250)
  }
  return () => {
    subscribers -= 1
    if (subscribers === 0 && clockInterval !== undefined) {
      clearInterval(clockInterval)
      clockInterval = undefined
    }
  }
}

export function cycleProgress(
  now: number,
  startedAt: string,
  cycleMs: number,
): number {
  if (cycleMs <= 0) return 0
  const elapsed = Math.max(0, now - Date.parse(startedAt))
  return (elapsed % cycleMs) / cycleMs
}

export function nextCycleDelay(
  now: number,
  startedAt: string,
  cycleMs: number,
  random: () => number = Math.random,
): number {
  const started = Date.parse(startedAt)
  const elapsed = Math.max(0, now - started)
  const untilBoundary = cycleMs - (elapsed % cycleMs || 0)
  const jitter = cycleMs * 0.1 * (random() * 2 - 1)
  return Math.max(100, untilBoundary + jitter)
}
