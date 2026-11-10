import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { PaperAccount, PaperTrade, Quote, PaperControl } from '../types'

const inr = (value: number) => `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
const stamp = (value: string | null) => value ? new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—'

export default function PaperTrading({ symbols, liveQuotes }: { symbols: string[]; liveQuotes: Quote[] }) {
  const [account, setAccount] = useState<PaperAccount | null>(null)
  const [trades, setTrades] = useState<PaperTrade[]>([])
  const [quotes, setQuotes] = useState<Quote[]>([])
  const [control, setControl] = useState<PaperControl | null>(null)
  const [symbol, setSymbol] = useState(symbols[0] || 'RELIANCE')
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY')
  const [quantity, setQuantity] = useState(1)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function refresh() {
    const [a, t, c] = await Promise.all([api.account(), api.trades(), api.paperControl()])
    setAccount(a); setTrades(t.trades); setControl(c)
  }
  useEffect(() => { void refresh().catch(e => setError(e.message)) }, [])
  useEffect(() => { setQuotes(liveQuotes) }, [liveQuotes])
  useEffect(() => { if (symbols.length && !symbols.includes(symbol)) setSymbol(symbols[0]) }, [symbols.join(',')])
  useEffect(() => { const id = window.setInterval(() => { void refresh().catch(e => setError(e.message)) }, 5000); return () => window.clearInterval(id) }, [])

  async function submitOrder(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setMessage('')
    try {
      const result = await api.placePaperOrder({ symbol, side, quantity })
      setAccount(result.account)
      setMessage(`${result.message}: ${quantity} ${symbol} @ ${inr(result.trade.price)} (fees ${inr(result.trade.fees)})`)
      await refresh()
    } catch (e) { setError(e instanceof Error ? e.message : 'Order could not be placed') }
    finally { setBusy(false) }
  }

  const quote = quotes.find(q => q.symbol === symbol)
  return <section className="section">
    <div className="section-heading"><div><h2>Paper trading simulator</h2><p>Live quote-based simulated fills · 0.10% fee per side · No broker orders</p><p className="muted small">Per-order limit: {inr(control?.max_order_value ?? 25000)}</p></div><div className="paper-control-actions"><span className="paper-tag">{control?.enabled ? "SIMULATOR ENABLED" : "SIMULATOR PAUSED"}</span><button type="button" className="text-button" onClick={async () => { try { const next = await api.updatePaperControl(!(control?.enabled ?? true)); setControl(next); setMessage(next.enabled ? "Paper trading enabled" : "Paper trading paused") } catch (e) { setError(e instanceof Error ? e.message : "Could not update trading control") } }}>{control?.enabled ? "Pause trading" : "Resume trading"}</button></div></div>
    <div className="paper-layout">
      <form className="panel paper-order-form" onSubmit={submitOrder}>
        <div className="paper-form-title">Place simulated order</div>
        <label>Instrument<select value={symbol} onChange={e => setSymbol(e.target.value)}>{symbols.map(s => <option key={s} value={s}>{s}</option>)}</select></label>
        <div className="paper-side-toggle"><button type="button" className={side === 'BUY' ? 'buy-selected' : ''} onClick={() => setSide('BUY')}>BUY</button><button type="button" className={side === 'SELL' ? 'sell-selected' : ''} onClick={() => setSide('SELL')}>SELL</button></div>
        <label>Quantity<input type="number" min="1" max="10000" step="1" value={quantity} onChange={e => setQuantity(Math.max(1, Math.min(10000, Number(e.target.value) || 1)))}/></label>
        <div className="paper-estimate"><span>Indicative price</span><strong>{quote ? inr(quote.last_price) : 'Loading…'}</strong></div>
        <div className="paper-estimate"><span>Estimated order value</span><strong>{quote ? inr(quote.last_price * quantity) : '—'}</strong></div>
        <button className="paper-submit" type="submit" disabled={busy || !quote || !control?.enabled || quote.last_price * quantity > (control?.max_order_value ?? 25000)}>{busy ? 'Processing…' : `Place paper ${side} order`}</button>
        {message && <div className="paper-success">{message}</div>}{error && <div className="paper-error">{error}</div>}
        <p className="paper-disclaimer">Orders fill immediately at the latest available provider quote, subject to the simulator kill switch and ₹25,000 per-order limit. Demo mode uses synthetic prices. Fees are a simplified simulation, not actual brokerage or statutory charges.</p>
      </form>
      <div className="paper-right">
        <div className="account-grid paper-metrics">
          <div className="metric-card"><div className="metric-label">Cash available</div><div className="metric-value">{inr(account?.cash_balance ?? 0)}</div></div>
          <div className="metric-card"><div className="metric-label">Holdings value</div><div className="metric-value">{inr(account?.invested_value ?? 0)}</div></div>
          <div className="metric-card"><div className="metric-label">Realized P&amp;L</div><div className={`metric-value ${(account?.realized_pnl ?? 0) >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>{inr(account?.realized_pnl ?? 0)}</div></div>
          <div className="metric-card"><div className="metric-label">Unrealized P&amp;L</div><div className={`metric-value ${(account?.unrealized_pnl ?? 0) >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>{inr(account?.unrealized_pnl ?? 0)}</div></div>
        </div>
        <div className="panel paper-table-panel"><div className="paper-table-title">Open positions</div><div className="table-wrap"><table><thead><tr><th>Symbol</th><th>Qty</th><th>Avg. cost</th><th>LTP</th><th>Unrealized P&amp;L</th></tr></thead><tbody>
          {account?.positions.length ? account.positions.map(p => <tr key={p.symbol}><td className="symbol">{p.symbol}</td><td>{p.quantity}</td><td>{inr(p.average_price)}</td><td>{inr(p.last_price)}</td><td className={p.unrealized_pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}>{inr(p.unrealized_pnl)}</td></tr>) : <tr><td colSpan={5} className="paper-empty">No open positions yet. Place a paper BUY to get started.</td></tr>}
        </tbody></table></div></div>
      </div>
    </div>
    <div className="panel paper-table-panel paper-trades" id="journal"><div className="paper-table-title">Trade journal</div><div className="table-wrap"><table><thead><tr><th>Time</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Fill price</th><th>Fees</th><th>Realized P&amp;L</th></tr></thead><tbody>
      {trades.length ? trades.map(t => <tr key={t.id}><td>{stamp(t.created_at)}</td><td className="symbol">{t.symbol}</td><td><span className={`pill ${t.side === 'BUY' ? 'buy' : 'avoid'}`}>{t.side}</span></td><td>{t.quantity}</td><td>{inr(t.price)}</td><td>{inr(t.fees)}</td><td className={t.realized_pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}>{inr(t.realized_pnl)}</td></tr>) : <tr><td colSpan={7} className="paper-empty">Your simulated fills will appear here.</td></tr>}
    </tbody></table></div></div>
  </section>
}
