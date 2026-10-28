import { useEffect, useRef, useState } from 'react'
import { PauseIcon, PlayIcon } from '../common/icons'
import type { PltFrameMeta, TimeUnit } from '../../types'
import { formatTime } from '../../utils/time'

type Props = {
  frames: PltFrameMeta[]
  position: number
  onPositionChange: (position: number) => void
  timeUnit: TimeUnit
  onTimeUnitChange: (unit: TimeUnit) => void
}

const PLAYBACK_INTERVAL_MS = 400

export default function TimeSlider({ frames, position, onPositionChange, timeUnit, onTimeUnitChange }: Props) {
  const [playing, setPlaying] = useState(false)
  const positionRef = useRef(position)
  positionRef.current = position

  useEffect(() => {
    if (!playing) return
    const timer = setInterval(() => {
      const next = (positionRef.current + 1) % frames.length
      onPositionChange(next)
    }, PLAYBACK_INTERVAL_MS)
    return () => clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, frames.length])

  useEffect(() => {
    setPlaying(false)
  }, [frames])

  const frame = frames[position]

  return (
    <div className="time-slider">
      <div className="time-slider__header">
        <span>時間フレーム</span>
        <span className="time-slider__value">
          {frame ? formatTime(frame.time_sec, timeUnit) : '-'}（{position + 1}/{frames.length}）
        </span>
      </div>
      <div className="time-slider__row">
        <button
          type="button"
          className="btn-secondary time-slider__play"
          onClick={() => setPlaying((p) => !p)}
          disabled={frames.length <= 1}
        >
          {playing ? <PauseIcon className="btn-icon" /> : <PlayIcon className="btn-icon" />}
        </button>
        <input
          type="range"
          min={0}
          max={Math.max(0, frames.length - 1)}
          step={1}
          value={position}
          onChange={(e) => {
            setPlaying(false)
            onPositionChange(Number(e.target.value))
          }}
        />
      </div>
      <div className="segmented" role="radiogroup" aria-label="時間の単位">
        {(['sec', 'hour'] as TimeUnit[]).map((unit) => (
          <label key={unit} className={`segmented__option ${timeUnit === unit ? 'is-active' : ''}`}>
            <input
              type="radio"
              name="time-slider-unit"
              checked={timeUnit === unit}
              onChange={() => onTimeUnitChange(unit)}
            />
            {unit === 'sec' ? '秒' : '時間'}
          </label>
        ))}
      </div>
    </div>
  )
}
