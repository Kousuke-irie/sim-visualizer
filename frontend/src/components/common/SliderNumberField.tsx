type Props = {
  label: string
  value: number
  min: number
  max: number
  step?: number
  unit?: string
  onChange: (value: number) => void
}

export default function SliderNumberField({ label, value, min, max, step = 1, unit, onChange }: Props) {
  return (
    <div className="field slider-field">
      <div className="slider-field__header">
        <span>{label}</span>
        <span className="slider-field__value">
          {value}
          {unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  )
}
