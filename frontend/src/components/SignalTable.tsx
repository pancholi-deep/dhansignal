import { Fragment, useState } from 'react'
import type { Signal } from '../types'

const money = (value: number | null) =>
  value == null ? '—' : `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`

export function SignalTable({ signals, onPrepareTrade }: { signals: Signal[]; onPrepareTrade: (symbol: string) => void }) {
  const [expanded, setExpanded] = useState<string | null>(null)

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Stock</th>
            <th title="Rule-based action: BUY, WAIT or AVOID. It is a strategy output, not a guarantee.">Signal <span className="help-bubble">i</span></th>
            <th title="Strategy score out of 10 from the configured technical rules. Higher is stronger within this strategy only.">Score <span className="help-bubble">i</span></th>
            <th>Price</th>
            <th title="Indicative strategy entry level; check current liquidity and price before acting.">Entry <span className="help-bubble">i</span></th>
            <th title="Indicative risk-control level. Actual execution can differ due to gaps and slippage.">Stop-loss <span className="help-bubble">i</span></th>
            <th title="Indicative strategy target, not a forecast or assured return.">Target <span className="help-bubble">i</span></th>
            <th title="Relative Strength Index over 14 periods; above 70 is often considered overbought and below 30 oversold.">RSI <span className="help-bubble">i</span></th>
            <th>Why?</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((signal) => (
            <Fragment key={signal.symbol}>
              <tr>
                <td className="symbol">{signal.symbol}</td>
                <td>
                  <span className={`pill ${signal.action.toLowerCase()}`}>
                    {signal.action}
                  </span>
                </td>
                <td>{signal.score.toFixed(1)}/10</td>
                <td>{money(signal.price)}</td>
                <td>{money(signal.entry_price)}</td>
                <td>{money(signal.stop_loss)}</td>
                <td>{money(signal.target_price)}</td>
                <td>{signal.rsi_14.toFixed(1)}</td>
                <td>
                  <div className="signal-actions">
                    {signal.action !== 'AVOID' && <button type="button" className="text-button" onClick={() => onPrepareTrade(signal.symbol)}>Prepare BUY</button>}
                    <button
                    type="button"
                    className="text-button"
                    onClick={() =>
                      setExpanded(
                        expanded === signal.symbol ? null : signal.symbol,
                      )
                    }
                  >
                    {expanded === signal.symbol ? 'Hide' : 'Details'}
                    </button>
                  </div>
                </td>
              </tr>
              {expanded === signal.symbol && (
                <tr>
                  <td colSpan={9}>
                    <ul className="signal-rationale">
                      {signal.rationale.map((reason, index) => (
                        <li key={index}>{reason}</li>
                      ))}
                    </ul>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}
