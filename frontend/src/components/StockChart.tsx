import { useEffect, useRef, useState } from 'react'
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineStyle,
} from 'lightweight-charts'
import type { UTCTimestamp } from 'lightweight-charts'
import type { Candle } from '../types'
import { api } from '../services/api'

const SYMBOLS = ['RELIANCE', 'HDFCBANK', 'INFY', 'ICICIBANK', 'TCS', 'LT']
const WINDOWS = [
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
]

function chartTime(date: string): UTCTimestamp {
  return Math.floor(new Date(`${date}T00:00:00Z`).getTime() / 1000) as UTCTimestamp
}

const chartOptions = {
  layout: {
    background: { type: ColorType.Solid, color: '#111827' },
    textColor: '#9ca3af',
    fontFamily: 'Inter, sans-serif',
  },
  grid: {
    vertLines: { color: '#202938' },
    horzLines: { color: '#202938' },
  },
  crosshair: { mode: CrosshairMode.Normal },
  rightPriceScale: { borderColor: '#374151' },
  timeScale: { borderColor: '#374151', timeVisible: false, rightOffset: 5 },
}

export default function StockChart() {
  const priceRef = useRef<HTMLDivElement>(null)
  const volumeRef = useRef<HTMLDivElement>(null)
  const rsiRef = useRef<HTMLDivElement>(null)
  const macdRef = useRef<HTMLDivElement>(null)
  const [symbol, setSymbol] = useState('RELIANCE')
  const [days, setDays] = useState(180)
  const [candles, setCandles] = useState<Candle[]>([])
  const [provider, setProvider] = useState('')
  const [isLive, setIsLive] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false

    async function loadHistory() {
      setLoading(true)
      setError('')
      try {
        const response = await api.history(symbol, 365)
        if (cancelled) return
        const cutoff = new Date()
        cutoff.setDate(cutoff.getDate() - days)
        setCandles(response.candles.filter(candle => new Date(candle.date) >= cutoff))
        setProvider(response.provider)
        setIsLive(response.is_live)
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Unable to load chart data')
          setCandles([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void loadHistory()
    return () => { cancelled = true }
  }, [symbol, days])

  useEffect(() => {
    if (!candles.length || !priceRef.current || !volumeRef.current || !rsiRef.current || !macdRef.current) return

    const priceChart = createChart(priceRef.current, { ...chartOptions, height: 380, autoSize: true })
    const candleSeries = priceChart.addCandlestickSeries({
      upColor: '#22c55e', downColor: '#ef4444',
      borderUpColor: '#22c55e', borderDownColor: '#ef4444',
      wickUpColor: '#22c55e', wickDownColor: '#ef4444',
    })
    const ema20 = priceChart.addLineSeries({ color: '#facc15', lineWidth: 2, title: 'EMA 20', lastValueVisible: false })
    const ema50 = priceChart.addLineSeries({ color: '#38bdf8', lineWidth: 2, title: 'EMA 50', lastValueVisible: false })
    const ema200 = priceChart.addLineSeries({ color: '#c084fc', lineWidth: 2, title: 'EMA 200', lastValueVisible: false })

    candleSeries.setData(candles.map(c => ({
      time: chartTime(c.date), open: c.open, high: c.high, low: c.low, close: c.close,
    })))
    ema20.setData(candles.filter(c => c.ema_20 != null).map(c => ({ time: chartTime(c.date), value: c.ema_20! })))
    ema50.setData(candles.filter(c => c.ema_50 != null).map(c => ({ time: chartTime(c.date), value: c.ema_50! })))
    ema200.setData(candles.filter(c => c.ema_200 != null).map(c => ({ time: chartTime(c.date), value: c.ema_200! })))
    priceChart.timeScale().fitContent()

    const volumeChart = createChart(volumeRef.current, { ...chartOptions, height: 125, autoSize: true })
    const volumeSeries = volumeChart.addHistogramSeries({ priceFormat: { type: 'volume' }, priceScaleId: '', lastValueVisible: false })
    volumeChart.priceScale('').applyOptions({ scaleMargins: { top: 0.1, bottom: 0 } })
    volumeSeries.setData(candles.map(c => ({
      time: chartTime(c.date), value: c.volume,
      color: c.close >= c.open ? 'rgba(34,197,94,0.55)' : 'rgba(239,68,68,0.55)',
    })))
    volumeChart.timeScale().fitContent()

    const rsiChart = createChart(rsiRef.current, { ...chartOptions, height: 155, autoSize: true })
    const rsiSeries = rsiChart.addLineSeries({ color: '#e879f9', lineWidth: 2, title: 'RSI 14', priceLineVisible: false })
    rsiSeries.setData(candles.filter(c => c.rsi_14 != null).map(c => ({ time: chartTime(c.date), value: c.rsi_14! })))
    rsiSeries.createPriceLine({ price: 70, color: '#ef4444', lineStyle: LineStyle.Dashed, title: '70' })
    rsiSeries.createPriceLine({ price: 30, color: '#22c55e', lineStyle: LineStyle.Dashed, title: '30' })
    rsiChart.timeScale().fitContent()

    const macdChart = createChart(macdRef.current, { ...chartOptions, height: 155, autoSize: true })
    const macdHistogram = macdChart.addHistogramSeries({ title: 'MACD histogram', priceLineVisible: false })
    const macdLine = macdChart.addLineSeries({ color: '#38bdf8', lineWidth: 2, title: 'MACD', priceLineVisible: false })
    const signalLine = macdChart.addLineSeries({ color: '#f97316', lineWidth: 2, title: 'Signal', priceLineVisible: false })
    macdHistogram.setData(candles.filter(c => c.macd_histogram != null).map(c => ({
      time: chartTime(c.date), value: c.macd_histogram!,
      color: c.macd_histogram! >= 0 ? '#22c55e' : '#ef4444',
    })))
    macdLine.setData(candles.filter(c => c.macd != null).map(c => ({ time: chartTime(c.date), value: c.macd! })))
    signalLine.setData(candles.filter(c => c.macd_signal != null).map(c => ({ time: chartTime(c.date), value: c.macd_signal! })))
    macdChart.timeScale().fitContent()

    return () => {
      priceChart.remove()
      volumeChart.remove()
      rsiChart.remove()
      macdChart.remove()
    }
  }, [candles])

  return (
    <section className="section stock-chart-section">
      <div className="section-heading">
        <div><h2>Technical analysis</h2><p>Price action, trend and momentum indicators</p></div>
        <span className={`provider-tag ${isLive ? 'live' : 'demo'}`}><span />{provider || 'LOADING'}</span>
      </div>
      <div className="chart-toolbar">
        <select value={symbol} onChange={e => setSymbol(e.target.value)} aria-label="Select stock">
          {SYMBOLS.map(item => <option key={item} value={item}>{item}</option>)}
        </select>
        <div className="chart-periods">
          {WINDOWS.map(window => (
            <button key={window.label} className={days === window.days ? 'selected' : ''} onClick={() => setDays(window.days)}>
              {window.label}
            </button>
          ))}
        </div>
      </div>
      {!isLive && provider && <div className="demo-banner chart-demo-notice">Synthetic demo prices — not actual NSE/BSE market quotes.</div>}
      {loading && <p className="chart-message">Loading historical data…</p>}
      {error && <p className="chart-error">{error}</p>}
      {!loading && !error && candles.length === 0 && <p className="chart-message">No historical candles available.</p>}
      {candles.length > 0 && (
        <div className="chart-panel">
          <div className="chart-legend"><span className="legend-ema20">EMA 20</span><span className="legend-ema50">EMA 50</span><span className="legend-ema200">EMA 200</span></div>
          <div ref={priceRef} className="chart-canvas" />
          <div className="chart-subtitle">VOLUME</div>
          <div ref={volumeRef} className="chart-canvas" />
          <div className="chart-subtitle">RELATIVE STRENGTH INDEX · 14</div>
          <div ref={rsiRef} className="chart-canvas" />
          <div className="chart-subtitle">MACD · 12, 26, 9</div>
          <div ref={macdRef} className="chart-canvas" />
        </div>
      )}
    </section>
  )
}
