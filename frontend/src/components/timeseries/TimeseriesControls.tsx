import type { ReactNode } from 'react'
import { GridIcon, ImageIcon, LayersIcon } from '../common/icons'
import RangeField from '../common/RangeField'
import SliderNumberField from '../common/SliderNumberField'
import type { DatMeta, TimeseriesParams, TimeUnit } from '../../types'

type Props = {
  meta: Pick<DatMeta, 'depths' | 'variable'>
  params: TimeseriesParams
  onChange: (patch: Partial<TimeseriesParams>) => void
}

function ControlGroup({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <div className="control-group">
      <div className="control-group__header">
        {icon}
        <span>{title}</span>
      </div>
      <div className="control-group__body">{children}</div>
    </div>
  )
}

export default function TimeseriesControls({ meta, params, onChange }: Props) {
  function toggleDepth(depth: string, checked: boolean) {
    const next = checked ? [...params.selectedDepths, depth] : params.selectedDepths.filter((d) => d !== depth)
    onChange({ selectedDepths: meta.depths.filter((d) => next.includes(d)) })
  }

  const allSelected = params.selectedDepths.length === meta.depths.length

  return (
    <div className="section-controls">
      <ControlGroup icon={<LayersIcon className="control-group__icon" />} title="表示する深度">
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={allSelected}
            onChange={(e) => onChange({ selectedDepths: e.target.checked ? [...meta.depths] : [] })}
          />
          全選択
        </label>
        {meta.depths.map((depth) => (
          <label key={depth} className="checkbox-field">
            <input
              type="checkbox"
              checked={params.selectedDepths.includes(depth)}
              onChange={(e) => toggleDepth(depth, e.target.checked)}
            />
            {depth}
          </label>
        ))}
      </ControlGroup>

      <ControlGroup icon={<GridIcon className="control-group__icon" />} title="軸・レイアウト">
        <div className="segmented" role="radiogroup" aria-label="時間軸の単位">
          {(['sec', 'hour'] as TimeUnit[]).map((unit) => (
            <label key={unit} className={`segmented__option ${params.timeUnit === unit ? 'is-active' : ''}`}>
              <input
                type="radio"
                name="time-unit"
                checked={params.timeUnit === unit}
                onChange={() => onChange({ timeUnit: unit })}
              />
              {unit === 'sec' ? '秒' : '時間'}
            </label>
          ))}
        </div>
        <RangeField label="時間軸範囲" value={params.timeRange} onChange={(timeRange) => onChange({ timeRange })} />
        <RangeField label="値軸範囲" value={params.valueRange} onChange={(valueRange) => onChange({ valueRange })} />
        <label className="text-field">
          <span>タイトル</span>
          <input
            type="text"
            placeholder="未入力時は自動生成"
            value={params.axis.title ?? ''}
            onChange={(e) => onChange({ axis: { ...params.axis, title: e.target.value || undefined } })}
          />
        </label>
        <label className="text-field">
          <span>横軸ラベル</span>
          <input
            type="text"
            placeholder={params.timeUnit === 'sec' ? 'time [sec]' : 'time [hour]'}
            value={params.axis.xlabel ?? ''}
            onChange={(e) => onChange({ axis: { ...params.axis, xlabel: e.target.value || undefined } })}
          />
        </label>
        <label className="text-field">
          <span>縦軸ラベル</span>
          <input
            type="text"
            placeholder={meta.variable}
            value={params.axis.ylabel ?? ''}
            onChange={(e) => onChange({ axis: { ...params.axis, ylabel: e.target.value || undefined } })}
          />
        </label>
      </ControlGroup>

      <ControlGroup icon={<ImageIcon className="control-group__icon" />} title="ダウンロード解像度">
        <SliderNumberField
          label="解像度倍率"
          value={params.exportScale}
          min={1}
          max={6}
          step={0.5}
          onChange={(v) => onChange({ exportScale: v })}
        />
      </ControlGroup>
    </div>
  )
}
