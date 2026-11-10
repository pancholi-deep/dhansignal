type Props = { label: string; value: string; change?: string; positive?: boolean; icon?: string }
export function MetricCard({ label, value, change, positive }: Props) {
  return <div className="metric-card"><div className="metric-label">{label}</div><div className="metric-value">{value}</div>{change && <div className={`metric-change ${positive ? 'positive' : 'negative'}`}>{change}</div>}</div>
}
