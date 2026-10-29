import { useState } from 'react'
import DirectoryComparePanel from './DirectoryComparePanel'
import DirectoryOpen from './DirectoryOpen'
import NewRunPanel from './NewRunPanel'
import DirectorySectionPanel from './DirectorySectionPanel'
import DirectoryTimeseriesPanel from './DirectoryTimeseriesPanel'
import ErrorBanner from '../common/ErrorBanner'
import { runLabel } from './compareFigure'
import { openDirectory } from '../../api/client'
import type { DirectoryMeta } from '../../types'

type SubTab = 'section' | 'timeseries' | 'compare' | 'new-run'

export default function DirectoryView() {
  // 開いたランはすべて覚えておく（比較タブで A・B を選ぶため）。表示中のランは currentId
  const [runs, setRuns] = useState<DirectoryMeta[]>([])
  const [currentId, setCurrentId] = useState<string | null>(null)
  const meta = runs.find((r) => r.dir_id === currentId) ?? null
  const [opening, setOpening] = useState(false)
  const [openError, setOpenError] = useState<string | null>(null)
  const [subTab, setSubTab] = useState<SubTab>('section')

  // 「元のランと比較」で選ぶ A・B。変わるたびに比較タブを作り直して、その組で始める
  const [comparePair, setComparePair] = useState<{ a: string; b: string } | null>(null)

  async function openRuns(paths: string[]): Promise<DirectoryMeta[] | null> {
    setOpening(true)
    setOpenError(null)
    try {
      const opened: DirectoryMeta[] = []
      for (const path of paths) opened.push(await openDirectory(path))
      // 同じディレクトリを開き直したら、古いものと置き換える（一覧に重複させない）
      const roots = new Set(opened.map((m) => m.root))
      setRuns((prev) => [...prev.filter((r) => !roots.has(r.root)), ...opened])
      setCurrentId(opened[opened.length - 1].dir_id)
      return opened
    } catch (err) {
      setOpenError(err instanceof Error ? err.message : 'ディレクトリを開けませんでした')
      return null
    } finally {
      setOpening(false)
    }
  }

  async function handleOpen(path: string) {
    if (await openRuns([path])) setSubTab('section')
  }

  async function handleCompare(basePath: string, newPath: string) {
    const opened = await openRuns([basePath, newPath])
    if (!opened) return
    setComparePair({ a: opened[0].dir_id, b: opened[1].dir_id })
    setSubTab('compare')
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
          {runs.length > 1 && (
            <label className="text-field run-select">
              <span>表示中のラン</span>
              <select value={meta.dir_id} onChange={(e) => setCurrentId(e.target.value)}>
                {runs.map((r) => (
                  <option key={r.dir_id} value={r.dir_id}>
                    {runLabel(r.root)}
                  </option>
                ))}
              </select>
            </label>
          )}
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
            <label className={`segmented__option ${subTab === 'compare' ? 'is-active' : ''}`}>
              <input
                type="radio"
                name="directory-subtab"
                checked={subTab === 'compare'}
                onChange={() => setSubTab('compare')}
              />
              比較
            </label>
            <label className={`segmented__option ${subTab === 'new-run' ? 'is-active' : ''}`}>
              <input
                type="radio"
                name="directory-subtab"
                checked={subTab === 'new-run'}
                onChange={() => setSubTab('new-run')}
              />
              新しいラン
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
          <div hidden={subTab !== 'compare'}>
            {runs.length < 2 ? (
              <div className="plot-placeholder compare-hint">
                比較するには、もう1つランを開いてください（上の「ディレクトリを開く」から追加できます）
              </div>
            ) : (
              <DirectoryComparePanel
                key={comparePair ? `${comparePair.a}:${comparePair.b}` : 'opened-order'}
                runs={runs}
                initialA={comparePair?.a}
                initialB={comparePair?.b}
              />
            )}
          </div>
          {/* 開いたときだけ runner に問い合わせる（runner を起動していなくても他のタブは使える） */}
          {subTab === 'new-run' && (
            <NewRunPanel key={meta.dir_id} meta={meta} onOpenRun={handleOpen} onCompare={handleCompare} />
          )}
        </>
      )}
    </div>
  )
}
