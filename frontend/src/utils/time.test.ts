import { describe, expect, it } from 'vitest'
import { formatTime } from './time'

describe('formatTime', () => {
  it('秒表示は整数に丸める', () => {
    expect(formatTime(3599.6, 'sec')).toBe('3600 s')
  })

  it('時間表示は小数2桁', () => {
    expect(formatTime(5400, 'hour')).toBe('1.50 h')
  })
})
