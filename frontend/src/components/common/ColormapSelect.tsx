import { useEffect, useRef, useState } from 'react'

type Props = {
  label: string
  value: string
  options: string[]
  gradients: Record<string, string>
  onChange: (value: string) => void
}

export default function ColormapSelect({ label, value, options, gradients, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className="field colormap-select" ref={rootRef}>
      <span>{label}</span>
      <button type="button" className="colormap-select__trigger" onClick={() => setOpen((o) => !o)}>
        <span className="colormap-select__swatch" style={{ background: gradients[value] }} />
        <span className="colormap-select__label">{value}</span>
        <span className="colormap-select__chevron">▾</span>
      </button>
      {open && (
        <div className="colormap-select__menu" role="listbox">
          {options.map((name) => (
            <button
              key={name}
              type="button"
              role="option"
              aria-selected={name === value}
              className={`colormap-select__option ${name === value ? 'is-selected' : ''}`}
              onClick={() => {
                onChange(name)
                setOpen(false)
              }}
            >
              <span className="colormap-select__swatch" style={{ background: gradients[name] }} />
              <span className="colormap-select__label">{name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
