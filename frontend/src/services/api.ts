import type { Overview, Signal, WatchlistResponse, Candle, PaperAccount, PaperTrade, PaperOrderResult } from '../types'

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail || `API request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const api = {
  overview: () => request<Overview>('/market/overview'),
  watchlist: () => request<WatchlistResponse>('/market/watchlist'),
  signals: () => request<{ signals: Signal[]; provider: string }>('/signals'),
  account: () => request<PaperAccount>('/paper/account'),
  trades: () => request<{ trades: PaperTrade[] }>('/paper/trades'),
  placePaperOrder: (payload: { symbol: string; side: 'BUY' | 'SELL'; quantity: number }) =>
    request<PaperOrderResult>('/paper/orders', { method: 'POST', body: JSON.stringify(payload) }),
  history: (symbol: string, days = 365) =>
    request<{ symbol: string; provider: string; is_live: boolean; candles: Candle[] }>(
      `/market/history/${encodeURIComponent(symbol)}?interval=day&days=${days}`
    ),
}
