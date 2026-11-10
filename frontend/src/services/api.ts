import type { Overview, Signal, WatchlistResponse } from '../types'

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`API request failed (${response.status})`)
  return response.json() as Promise<T>
}
export const api = {
  overview: () => request<Overview>('/market/overview'),
  watchlist: () => request<WatchlistResponse>('/market/watchlist'),
  signals: () => request<{ signals: Signal[]; provider: string }>('/signals'),
  account: () => request<{ starting_cash: number; cash_balance: number; invested_value: number; unrealized_pnl: number; mode: string }>('/paper/account'),
}
