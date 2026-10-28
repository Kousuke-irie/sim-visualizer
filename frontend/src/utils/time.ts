import type { TimeUnit } from '../types'

export function formatTime(sec: number, unit: TimeUnit): string {
  return unit === 'hour' ? `${(sec / 3600).toFixed(2)} h` : `${sec.toFixed(0)} s`
}
