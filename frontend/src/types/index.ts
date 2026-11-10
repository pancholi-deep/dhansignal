export type Quote = { symbol: string; exchange: string; last_price: number; change: number; change_percent: number; volume: number; open?: number; high?: number; low?: number; close?: number; timestamp?: string | null }
export type IndexQuote = { symbol: string; last_price: number; change_percent: number }
export type Signal = { symbol: string; action: 'BUY' | 'WAIT' | 'AVOID'; score: number; price: number; entry_price: number | null; stop_loss: number | null; target_price: number | null; rsi_14: number; ema_50: number; ema_200: number; atr_14: number; volume_confirmed: boolean; holding_period: string | null; rationale: string[]; strategy_version: string; as_of: string }
export type Overview = { provider: string; is_live: boolean; indices: IndexQuote[] }
export type WatchlistResponse = { symbols: string[]; quotes: Quote[]; provider: string; is_live: boolean }
export type Candle = {
  date: string; open: number; high: number; low: number; close: number; volume: number
  ema_20: number | null; ema_50: number | null; ema_200: number | null
  rsi_14: number | null; macd: number | null; macd_signal: number | null; macd_histogram: number | null
}
export type PaperPosition = {
  symbol: string; quantity: number; average_price: number; last_price: number
  market_value: number; unrealized_pnl: number; realized_pnl: number
}
export type PaperAccount = {
  id: number; currency: string; starting_cash: number; cash_balance: number
  invested_value: number; total_value: number; realized_pnl: number
  unrealized_pnl: number; positions: PaperPosition[]; mode: 'PAPER'; provider: string
}
export type PaperTrade = {
  id: number; symbol: string; side: 'BUY' | 'SELL'; quantity: number
  price: number; fees: number; realized_pnl: number; created_at: string | null
}
export type PaperOrderResult = { message: string; trade: PaperTrade; account: PaperAccount }


export type ResearchDocument = {
  id: number; title: string; original_filename: string; document_type: string
  company_name: string; symbol: string | null; reporting_period: string | null
  file_size: number; page_count: number; status: string; created_at: string | null
  text_length: number; snippet?: string
}

export type ResearchEvidence = { id: number; document_id: number; title: string; company_name: string; symbol: string | null; document_type: string; reporting_period: string | null; page_number: number; chunk_index: number; content: string; score: number; matched_terms: string[] }

export type MarketStreamMessage = { type: 'ticks' | 'snapshot' | 'status'; provider?: string; is_live?: boolean; data: Quote[] }

export type PaperControl = { enabled: boolean; max_order_value: number }

export type KiteAuthStatus = { configured: boolean; authenticated: boolean; provider: string; stream_connected: boolean }
