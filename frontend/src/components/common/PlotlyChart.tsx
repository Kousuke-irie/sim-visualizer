import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import Plotly from 'plotly.js-dist-min'
import type { Config, Data, Layout } from 'plotly.js'

export type PlotlyChartHandle = {
  downloadImage: (opts: { filename: string; scale: number }) => Promise<void>
}

type Props = {
  data: Data[]
  layout: Partial<Layout>
  config?: Partial<Config>
  className?: string
  style?: React.CSSProperties
}

const PlotlyChart = forwardRef<PlotlyChartHandle, Props>(function PlotlyChart(
  { data, layout, config, className, style },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    Plotly.react(el, data, layout, config)
  }, [data, layout, config])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const observer = new ResizeObserver(() => {
      Plotly.Plots.resize(el)
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const el = containerRef.current
    return () => {
      if (el) Plotly.purge(el)
    }
  }, [])

  useImperativeHandle(ref, () => ({
    async downloadImage({ filename, scale }) {
      const el = containerRef.current
      if (!el) return
      // `scale` is a real runtime option (resolution multiplier) missing from @types/plotly.js.
      await Plotly.downloadImage(el, { format: 'png', filename, width: null, height: null, scale } as Parameters<
        typeof Plotly.downloadImage
      >[1])
    },
  }))

  return <div ref={containerRef} className={className} style={style} />
})

export default PlotlyChart
