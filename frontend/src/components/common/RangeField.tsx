type RangeValue = { auto: boolean; min?: number; max?: number }

type Props = {
  label: string
  value: RangeValue
  onChange: (value: RangeValue) => void
}

export default function RangeField({ label, value, onChange }: Props) {
  return (
    <div className="field range-field">
      <span>{label}</span>
      <label className="auto-toggle">
        <input type="checkbox" checked={value.auto} onChange={(e) => onChange({ ...value, auto: e.target.checked })} />
        自動
      </label>
      {!value.auto && (
        <div className="range-inputs">
          <input
            type="number"
            placeholder="min"
            value={value.min ?? ''}
            onChange={(e) => onChange({ ...value, min: e.target.value === '' ? undefined : Number(e.target.value) })}
          />
          <input
            type="number"
            placeholder="max"
            value={value.max ?? ''}
            onChange={(e) => onChange({ ...value, max: e.target.value === '' ? undefined : Number(e.target.value) })}
          />
        </div>
      )}
    </div>
  )
}
