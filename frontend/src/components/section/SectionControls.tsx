import type { ReactNode } from 'react'
import { AspectIcon, CompassIcon, GridIcon, ImageIcon, LayersIcon, PaletteIcon, WindIcon } from '../common/icons'
import ColorSwatchPicker from '../common/ColorSwatchPicker'
import ColormapSelect from '../common/ColormapSelect'
import NumberField from '../common/NumberField'
import RangeField from '../common/RangeField'
import SliderNumberField from '../common/SliderNumberField'
import { COLORMAP_GRADIENTS, COLORMAP_NAMES } from '../../constants'
import type { Plane, PltMeta, SectionParams } from '../../types'

type Props = {
  meta: Pick<PltMeta, 'variables'>
  params: SectionParams
  axisSize: number
  axisCoordLabel: string
  onPlaneChange: (plane: Plane) => void
  onChange: (patch: Partial<SectionParams>) => void
}

const PLANES: Plane[] = ['XY', 'XZ', 'YZ']

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

export default function SectionControls({ meta, params, axisSize, axisCoordLabel, onPlaneChange, onChange }: Props) {
  return (
    <div className="section-controls">
      <ControlGroup icon={<CompassIcon className="control-group__icon" />} title="断面方向">
        <div className="segmented" role="radiogroup" aria-label="断面方向">
          {PLANES.map((p) => (
            <label key={p} className={`segmented__option ${params.plane === p ? 'is-active' : ''}`}>
              <input type="radio" name="plane" checked={params.plane === p} onChange={() => onPlaneChange(p)} />
              {p}
            </label>
          ))}
        </div>
        <SliderNumberField
          label={`断面位置（${axisCoordLabel}方向 index）`}
          value={params.sliceIndex}
          min={0}
          max={Math.max(0, axisSize - 1)}
          onChange={(v) => onChange({ sliceIndex: Math.min(Math.max(0, Math.round(v)), Math.max(0, axisSize - 1)) })}
        />
      </ControlGroup>

      <ControlGroup icon={<AspectIcon className="control-group__icon" />} title="図の形状">
        <label className="auto-toggle">
          <input
            type="checkbox"
            checked={params.axis.aspect.auto}
            onChange={(e) =>
              onChange({ axis: { ...params.axis, aspect: { ...params.axis.aspect, auto: e.target.checked } } })
            }
          />
          自動（実寸比率）
        </label>
        {!params.axis.aspect.auto && (
          <SliderNumberField
            label="縦横比（高さ / 幅）"
            value={params.axis.aspect.ratio ?? 1}
            min={0.2}
            max={4}
            step={0.1}
            onChange={(v) => onChange({ axis: { ...params.axis, aspect: { ...params.axis.aspect, ratio: v } } })}
          />
        )}
      </ControlGroup>

      <ControlGroup icon={<LayersIcon className="control-group__icon" />} title="描画変数">
        <select value={params.variable} onChange={(e) => onChange({ variable: e.target.value })}>
          {meta.variables.map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>
      </ControlGroup>

      <ControlGroup icon={<PaletteIcon className="control-group__icon" />} title="カラーマップ・スケール">
        <div className="segmented" role="radiogroup" aria-label="カラーマップの種類">
          <label className={`segmented__option ${!params.customColormap.enabled ? 'is-active' : ''}`}>
            <input
              type="radio"
              name="colormap-mode"
              checked={!params.customColormap.enabled}
              onChange={() => onChange({ customColormap: { ...params.customColormap, enabled: false } })}
            />
            プリセット
          </label>
          <label className={`segmented__option ${params.customColormap.enabled ? 'is-active' : ''}`}>
            <input
              type="radio"
              name="colormap-mode"
              checked={params.customColormap.enabled}
              onChange={() => onChange({ customColormap: { ...params.customColormap, enabled: true } })}
            />
            カスタム
          </label>
        </div>

        {!params.customColormap.enabled ? (
          <ColormapSelect
            label="プリセット"
            value={params.colormap}
            options={COLORMAP_NAMES}
            gradients={COLORMAP_GRADIENTS}
            onChange={(v) => onChange({ colormap: v })}
          />
        ) : (
          <>
            <ColorSwatchPicker
              label="最低値の色"
              value={params.customColormap.low}
              onChange={(hex) => onChange({ customColormap: { ...params.customColormap, low: hex } })}
            />
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={params.customColormap.useMid}
                onChange={(e) => onChange({ customColormap: { ...params.customColormap, useMid: e.target.checked } })}
              />
              中間色を使う（3色グラデーション）
            </label>
            {params.customColormap.useMid && (
              <ColorSwatchPicker
                label="中間色"
                value={params.customColormap.mid}
                onChange={(hex) => onChange({ customColormap: { ...params.customColormap, mid: hex } })}
              />
            )}
            <ColorSwatchPicker
              label="最高値の色"
              value={params.customColormap.high}
              onChange={(hex) => onChange({ customColormap: { ...params.customColormap, high: hex } })}
            />
          </>
        )}

        <NumberField
          label="塗りコンター レベル数"
          value={params.fillLevels}
          min={2}
          max={200}
          onChange={(v) => onChange({ fillLevels: Math.round(v) })}
        />
        <NumberField
          label="等値線 レベル数"
          value={params.lineLevels}
          min={1}
          max={100}
          onChange={(v) => onChange({ lineLevels: Math.round(v) })}
        />
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={params.showContourLines}
            onChange={(e) => onChange({ showContourLines: e.target.checked })}
          />
          等値線を表示
        </label>
        <RangeField
          label="色範囲"
          value={{ auto: params.colorRange.auto, min: params.colorRange.vmin, max: params.colorRange.vmax }}
          onChange={(v) => onChange({ colorRange: { auto: v.auto, vmin: v.min, vmax: v.max } })}
        />
      </ControlGroup>

      <ControlGroup icon={<WindIcon className="control-group__icon" />} title="流速ベクトル">
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={params.vectors.show}
            onChange={(e) => onChange({ vectors: { ...params.vectors, show: e.target.checked } })}
          />
          表示する
        </label>
        {params.vectors.show && (
          <>
            <SliderNumberField
              label="間引き数"
              value={params.vectors.skip}
              min={1}
              max={20}
              onChange={(v) => onChange({ vectors: { ...params.vectors, skip: Math.max(1, Math.round(v)) } })}
            />
            <NumberField
              label="スケール（0=自動）"
              value={params.vectors.scale ?? 0}
              min={0}
              onChange={(v) => onChange({ vectors: { ...params.vectors, scale: v > 0 ? v : undefined } })}
            />
            <SliderNumberField
              label="矢印の太さ (px)"
              value={params.vectors.width}
              min={1}
              max={6}
              step={0.5}
              onChange={(v) => onChange({ vectors: { ...params.vectors, width: v } })}
            />
            <SliderNumberField
              label="矢印の大きさ (px)"
              value={params.vectors.headWidth}
              min={4}
              max={20}
              step={1}
              onChange={(v) => onChange({ vectors: { ...params.vectors, headWidth: v } })}
            />
          </>
        )}
      </ControlGroup>

      <ControlGroup icon={<GridIcon className="control-group__icon" />} title="軸・レイアウト">
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
            value={params.axis.xlabel ?? ''}
            onChange={(e) => onChange({ axis: { ...params.axis, xlabel: e.target.value || undefined } })}
          />
        </label>
        <label className="text-field">
          <span>縦軸ラベル</span>
          <input
            type="text"
            value={params.axis.ylabel ?? ''}
            onChange={(e) => onChange({ axis: { ...params.axis, ylabel: e.target.value || undefined } })}
          />
        </label>
        <label className="text-field">
          <span>凡例の単位</span>
          <input
            type="text"
            placeholder="例: ℃, psu, mg/L"
            value={params.axis.unit ?? ''}
            onChange={(e) => onChange({ axis: { ...params.axis, unit: e.target.value || undefined } })}
          />
        </label>
        <RangeField
          label="深度(Z)表示範囲"
          value={params.axis.zlim}
          onChange={(zlim) => onChange({ axis: { ...params.axis, zlim } })}
        />
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
