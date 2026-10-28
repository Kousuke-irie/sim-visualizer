import type { HistPoint, TimeseriesIndex } from '../../types'

type Props = {
  timeseries: TimeseriesIndex
  points: HistPoint[]
  param: string
  point: string
  onChange: (patch: { param?: string; point?: string }) => void
}

export default function PointParamSelect({ timeseries, points, param, point, onChange }: Props) {
  const availablePoints = timeseries.by_param[param] ?? []
  const pointByLabel = new Map(points.map((p) => [p.point, p]))

  return (
    <div className="time-slider-card point-param-select">
      <label className="text-field">
        <span>パラメータ</span>
        <select value={param} onChange={(e) => onChange({ param: e.target.value })}>
          {timeseries.params.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </label>
      <label className="text-field">
        <span>地点</span>
        <select value={point} onChange={(e) => onChange({ point: e.target.value })}>
          {availablePoints.map((p) => {
            const info = pointByLabel.get(p)
            return (
              <option key={p} value={p}>
                {p}
                {info ? `（i=${info.i}, j=${info.j}）` : ''}
              </option>
            )
          })}
        </select>
      </label>
    </div>
  )
}
