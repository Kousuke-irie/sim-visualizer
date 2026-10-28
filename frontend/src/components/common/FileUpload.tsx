import { ChangeEvent, useRef } from 'react'
import { UploadIcon } from './icons'

type Props = {
  accept: string
  label: string
  onSelect: (file: File) => void
  disabled?: boolean
}

export default function FileUpload({ accept, label, onSelect, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) onSelect(file)
    e.target.value = ''
  }

  return (
    <div className="file-upload">
      <button type="button" className="btn-primary" onClick={() => inputRef.current?.click()} disabled={disabled}>
        <UploadIcon className="btn-icon" />
        {disabled ? 'アップロード中…' : label}
      </button>
      <input ref={inputRef} type="file" accept={accept} onChange={handleChange} style={{ display: 'none' }} />
    </div>
  )
}
