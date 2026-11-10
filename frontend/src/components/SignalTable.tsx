import { useState } from 'react'
import type { Signal } from '../types'
const money = (value: number | null) => value == null ? '—' : `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
export function SignalTable({ signals }: { signals: Signal[] }) {
  const [expanded, setExpanded] = useState<string | null>(null)
  return <div className="table-wrap"><table><thead><tr><th>Stock</th><th>Signal</th><th>Score</th><th>Price</th><th>Entry</th><th>Stop-loss</th><th>Target</th><th>RSI</th><th>Why?</th></tr></thead><tbody>
    {signals.map(s => <tr key={s.symbol}><td className="symbol">{s.symbol}</td><td><span className={`pill ${s.action.toLowerCase()}`}>{s.action}</span></td><td>{s.score.toFixed(1)}/10</td><td>{money(s.price)}</td><td>{money(s.entry_price)}</td><td>{money(s.stop_loss)}</td><td>{money(s.target_price)}</td><td>{s.rsi_14.toFixed(1)}</td><td><button type="button" className="text-button" onClick={() => setExpanded(expanded === s.symbol ? null : s.symbol)}>{expanded === s.symbol ? 'Hide' : 'Details'}</button></td></tr>{expanded === s.symbol && <tr key={s.symbol + '-details'}><td colSpan={9}><ul className="signal-rationale">{s.rationale.map((reason, index) => <li key={index}>{reason}</li>)}</ul></td></tr>})}
  </tbody></table></div>
}
