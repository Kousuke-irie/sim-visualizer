import { useState } from 'react'
import DirectoryOpen from './DirectoryOpen'
import DirectorySectionPanel from './DirectorySectionPanel'
import DirectoryTimeseriesPanel from './DirectoryTimeseriesPanel'
import ErrorBanner from '../common/ErrorBanner'
import { openDirectory } from '../../api/client'
import type { DirectoryMeta } from '../../types'

type SubTab = 'section' | 'timeseries'

export default function DirectoryView() {
  const [meta, setMeta] = useState<DirectoryMeta | null>(null)
  const [opening, setOpening] = useState(false)
  const [openError, setOpenError] = useState<string | null>(null)
  const [subTab, setSubTab] = useState<SubTab>('section')

  async function handleOpen(path: string) {
    setOpening(true)
    setOpenError(null)
    try {
      const newMeta = await openDirectory(path)
      setMeta(newMeta)
      setSubTab('section')
    } catch (err) {
      setOpenError(err instanceof Error ? err.message : 'ディレクトリを開けませんでした')
    } finally {
      setOpening(false)
    }
  }

  return (
    <div className="section-view">
      <header className="section-view__header">
        <h2>ディレクトリモード</h2>
        <DirectoryOpen onOpen={handleOpen} disabled={opening} />
      </header>

      <ErrorBanner message={openError} onDismiss={() => setOpenError(null)} />

      {meta && (
        <>
          <div className="section-view__meta">
            <span className="chip chip--muted">{meta.root}</span>
            <span className="chip chip--muted">フレーム数 {meta.plt_frames.length}</span>
            <span className="chip chip--muted">地点数 {meta.points.length}</span>
            <span className="chip chip--muted">
              計算期間 0〜{meta.input.endtime.toFixed(0)}s（plt間隔 {meta.input.ifit2.toFixed(0)}s）
            </span>
          </div>

          <div
            className="segmented app__tabs"
            role="radiogroup"
            aria-label="ディレクトリモードの表示切替"
            style={{ marginBottom: '1.25rem' }}
          >
            <label className={`segmented__option ${subTab === 'section' ? 'is-active' : ''}`}>
              <input
                type="radio"
                name="directory-subtab"
                checked={subTab === 'section'}
                onChange={() => setSubTab('section')}
              />
              空間分布
            </label>
            <label className={`segmented__option ${subTab === 'timeseries' ? 'is-active' : ''}`}>
              <input
                type="radio"
                name="directory-subtab"
                checked={subTab === 'timeseries'}
                onChange={() => setSubTab('timeseries')}
              />
              時系列
            </label>
          </div>

          {/* 各タブの状態はパネル自身が持つ。key を dir_id にして、別のディレクトリを開いたら初期状態から始める。
              タブを切り替えても設定が消えないよう、非表示のタブもアンマウントせず hidden で隠す */}
          <div hidden={subTab !== 'section'}>
            <DirectorySectionPanel key={meta.dir_id} meta={meta} />
          </div>
          <div hidden={subTab !== 'timeseries'}>
            <DirectoryTimeseriesPanel key={meta.dir_id} meta={meta} />
          </div>
        </>
      )}
    </div>
  )
}
