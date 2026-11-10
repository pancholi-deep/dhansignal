import type { Overview, Signal, WatchlistResponse, Candle, PaperAccount, PaperTrade, PaperOrderResult, ResearchDocument, ResearchEvidence, PaperControl, KiteAuthStatus, StockIntelligence } from '../types'

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail || `API request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}
export const api = {
  overview: () => request<Overview>('/market/overview'),
  kiteAuthStatus: () => request<KiteAuthStatus>('/auth/zerodha/status'),
  watchlist: () => request<WatchlistResponse>('/market/watchlist'),
  searchInstruments: (q: string) => request<{ results: InstrumentSuggestion[] }>(`/market/instruments/search?q=${encodeURIComponent(q)}`),
  addWatchlistSymbol: (symbol: string) => request<{ message: string; symbol: string }>(`/market/watchlist/${encodeURIComponent(symbol)}`, { method: 'POST' }),
  removeWatchlistSymbol: (symbol: string) => request<{ message: string; symbol: string }>(`/market/watchlist/${encodeURIComponent(symbol)}`, { method: 'DELETE' }),
  signals: () => request<{ signals: Signal[]; provider: string }>('/signals'),
  stockIntelligence: (symbol: string) => request<StockIntelligence>(`/intelligence/${encodeURIComponent(symbol)}`, { method: 'POST' }),
  account: () => request<PaperAccount>('/paper/account'),
  paperControl: () => request<PaperControl>('/paper/control'),
  updatePaperControl: (enabled: boolean) => request<PaperControl>('/paper/control', { method: 'PUT', body: JSON.stringify({ enabled }) }),
  trades: () => request<{ trades: PaperTrade[] }>('/paper/trades'),
  placePaperOrder: (payload: { symbol: string; side: 'BUY' | 'SELL'; quantity: number }) =>
    request<PaperOrderResult>('/paper/orders', { method: 'POST', body: JSON.stringify(payload) }),
  researchDocuments: () => request<{ documents: ResearchDocument[]; count: number }>('/research/documents'),
  searchResearch: (q: string, symbol?: string) => request<{ results: ResearchDocument[]; count: number }>(
    `/research/search?q=${encodeURIComponent(q)}${symbol ? `&symbol=${encodeURIComponent(symbol)}` : ''}`
  ),
  retrieveResearch: (q: string, symbol?: string) => request<{ query: string; results: ResearchEvidence[]; count: number; retrieval: string }>(`/research/retrieve?q=${encodeURIComponent(q)}${symbol ? `&symbol=${encodeURIComponent(symbol)}` : ''}`),
  indexResearch: (id: number) => request<{ document_id: number; chunk_count?: number; message: string }>(`/research/documents/${id}/index`, { method: 'POST' }),
  uploadResearch: async (form: FormData) => {
    const response = await fetch(`${API}/research/documents`, { method: 'POST', body: form })
    if (!response.ok) { const body = await response.json().catch(() => null); throw new Error(body?.detail || `Upload failed (${response.status})`) }
    return response.json() as Promise<ResearchDocument>
  },
  history: (symbol: string, days = 365, interval: string = 'day') =>
    request<{ symbol: string; provider: string; is_live: boolean; candles: Candle[] }>(
      `/market/history/${encodeURIComponent(symbol)}?interval=${encodeURIComponent(interval)}&days=${days}`
    ),
}
