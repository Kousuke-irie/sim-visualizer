import { FormEvent, useState } from 'react'
import DirectoryBrowser from './DirectoryBrowser'
import { FolderIcon } from '../common/icons'

type Props = {
  onOpen: (path: string) => void
  disabled?: boolean
}

export default function DirectoryOpen({ onOpen, disabled }: Props) {
  const [path, setPath] = useState('')
  const [browsing, setBrowsing] = useState(false)
  // 参照ボタンを押すたびに値を進め、DirectoryBrowser の key に使う。
  // 既に開いている状態で再度押した場合も key が変わることで強制的に再マウントされ、
  // マウント済みディレクトリの再スキャンが必ず走る。
  const [browseRequestId, setBrowseRequestId] = useState(0)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (path.trim()) onOpen(path.trim())
  }

  function handleBrowseClick() {
    setBrowsing(true)
    setBrowseRequestId((n) => n + 1)
  }

  function handleBrowseSelect(selected: string) {
    setPath(selected)
    setBrowsing(false)
  }

  return (
    <div className="directory-open-wrapper">
      <form className="directory-open" onSubmit={handleSubmit}>
        <input
          type="text"
          className="directory-open__input"
          placeholder="例: /data/mecamamo"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          disabled={disabled}
        />
        <button type="button" className="btn-secondary" onClick={handleBrowseClick} disabled={disabled}>
          参照…
        </button>
        <button type="submit" className="btn-primary" disabled={disabled || !path.trim()}>
          <FolderIcon className="btn-icon" />
          {disabled ? '読み込み中…' : 'ディレクトリを開く'}
        </button>
      </form>

      {browsing && (
        <DirectoryBrowser
          key={browseRequestId}
          initialPath={path || undefined}
          onSelect={handleBrowseSelect}
          onCancel={() => setBrowsing(false)}
        />
      )}
    </div>
  )
}
