import { COLOR_PALETTE } from '../../constants'

type Props = {
  label: string
  value: string
  onChange: (hex: string) => void
}

export default function ColorSwatchPicker({ label, value, onChange }: Props) {
  return (
    <div className="field color-swatch-field">
      <span>{label}</span>
      <div className="color-swatch-grid">
        {COLOR_PALETTE.map((hex) => (
          <button
            key={hex}
            type="button"
            className={`color-swatch ${value.toLowerCase() === hex.toLowerCase() ? 'is-selected' : ''}`}
            style={{ background: hex }}
            onClick={() => onChange(hex)}
            aria-label={hex}
            title={hex}
          />
        ))}
      </div>
    </div>
  )
}
