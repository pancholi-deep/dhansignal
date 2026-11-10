type Props = { label: string; value: string; change?: string; positive?: boolean; icon?: string }
const metricHelp: Record<string, string> = {
  'Starting capital': 'Initial virtual cash allocated to the paper account. It is not real money.',
  'Available cash': 'Uninvested virtual cash available for new simulated BUY orders.',
  'Invested value': 'Current market value of open paper positions, based on the latest available quote.',
  'Unrealized P&L': 'Estimated profit or loss on open positions. It changes with the latest quote and is not realized until a simulated SELL.',
}
export function MetricCard({ label, value, change, positive }: Props) {
  return <div className="metric-card"><div className="metric-label">{label}<span className="help-bubble" title={metricHelp[label] || "Metric calculated from the current paper account snapshot."}>i</span></div><div className="metric-value">{value}</div>{change && <div className={`metric-change ${positive ? 'positive' : 'negative'}`}>{change}</div>}</div>
}
