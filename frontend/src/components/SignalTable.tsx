import { useState } from 'react'
import type { Signal } from '../types'

const money = (value: number | null) =>
  value == null ? '—' : `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`

export function SignalTable({ signals }: { signals: Signal[] }) {
  const [expanded, setExpanded] = useState<string | null>(null)

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Stock</th>
            <th>Signal</th>
            <th>Score</th>
            <th>Price</th>
            <th>Entry</th>
            <th>Stop-loss</th>
            <th>Target</th>
            <th>RSI</th>
            <th>Why?</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((signal) => (
            <>
              <tr key={signal.symbol}>
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
            </>
          ))}
        </tbody>
      </table>
    </div>
  )
}
