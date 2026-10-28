import { useState } from 'react'
import SectionView from './components/section/SectionView'
import TimeseriesView from './components/timeseries/TimeseriesView'
import DirectoryView from './components/directory/DirectoryView'

type Tab = 'section' | 'timeseries' | 'directory'

export default function App() {
  const [tab, setTab] = useState<Tab>('section')

  return (
    <div className="app">
      <header className="app__navbar">
        <div className="app__brand">
          <span className="app__logo">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 17l5-6 4 4 5-8 4 5" />
            </svg>
          </span>
          <div className="app__brand-text">
            <span className="app__title">Sim Visualizer</span>
            <span className="app__subtitle">海洋・生態系シミュレーション可視化</span>
          </div>
        </div>
        <div className="segmented app__tabs" role="radiogroup" aria-label="表示切替">
          <label className={`segmented__option ${tab === 'section' ? 'is-active' : ''}`}>
            <input type="radio" name="tab" checked={tab === 'section'} onChange={() => setTab('section')} />
            断面ビュー
          </label>
          <label className={`segmented__option ${tab === 'timeseries' ? 'is-active' : ''}`}>
            <input type="radio" name="tab" checked={tab === 'timeseries'} onChange={() => setTab('timeseries')} />
            時系列ビュー
          </label>
          <label className={`segmented__option ${tab === 'directory' ? 'is-active' : ''}`}>
            <input type="radio" name="tab" checked={tab === 'directory'} onChange={() => setTab('directory')} />
            ディレクトリモード
          </label>
        </div>
      </header>
      <main className="app__main">
        {tab === 'section' && <SectionView />}
        {tab === 'timeseries' && <TimeseriesView />}
        {tab === 'directory' && <DirectoryView />}
      </main>
    </div>
  )
}
