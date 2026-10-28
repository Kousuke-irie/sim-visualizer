import { useEffect, useState } from 'react'
import { browseDirectory } from '../../api/client'
import { FolderIcon } from '../common/icons'
import type { DirectoryBrowseResponse } from '../../types'

type Props = {
  initialPath?: string
  onSelect: (path: string) => void
  onCancel: () => void
}

export default function DirectoryBrowser({ initialPath, onSelect, onCancel }: Props) {
  const [currentPath, setCurrentPath] = useState<string | undefined>(initialPath)
  const [data, setData] = useState<DirectoryBrowseResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    browseDirectory(currentPath)
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [currentPath])

  return (
    <div className="directory-browser">
      <div className="directory-browser__path">
        <button
          type="button"
          className="btn-secondary"
          onClick={() => data?.parent && setCurrentPath(data.parent)}
          disabled={!data?.parent}
        >
          ↑ 上へ
        </button>
        <span className="directory-browser__current">{data?.path ?? currentPath ?? '読み込み中…'}</span>
      </div>

      <div className="directory-browser__list">
        {loading && <div className="directory-browser__hint">読み込み中…</div>}
        {!loading && error && <div className="directory-browser__hint directory-browser__hint--error">{error}</div>}
        {!loading && !error && data?.entries.length === 0 && (
          <div className="directory-browser__hint">サブディレクトリがありません</div>
        )}
        {!loading &&
          !error &&
          data?.entries.map((entry) => (
            <button
              key={entry.path}
              type="button"
              className="directory-browser__item"
              onClick={() => setCurrentPath(entry.path)}
            >
              <FolderIcon className="btn-icon" />
              <span className="directory-browser__item-name">{entry.name}</span>
              {entry.has_input_dat && <span className="chip">input.dat</span>}
            </button>
          ))}
      </div>

      <div className="directory-browser__footer">
        <button type="button" className="btn-secondary" onClick={onCancel}>
          キャンセル
        </button>
        <button type="button" className="btn-primary" onClick={() => data && onSelect(data.path)} disabled={!data}>
          このフォルダを選択
        </button>
      </div>
    </div>
  )
}
