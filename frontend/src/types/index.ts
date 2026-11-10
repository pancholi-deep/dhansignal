export type Quote = { symbol: string; exchange: string; last_price: number; change: number; change_percent: number; volume: number; timestamp?: string | null }
export type IndexQuote = { symbol: string; last_price: number; change_percent: number }
export type Signal = { symbol: string; action: 'BUY' | 'WAIT' | 'AVOID'; score: number; price: number; entry_price: number | null; stop_loss: number | null; target_price: number | null; rsi_14: number; ema_50: number; ema_200: number; atr_14: number; volume_confirmed: boolean; holding_period: string | null; rationale: string[]; strategy_version: string; as_of: string }
export type Overview = { provider: string; is_live: boolean; indices: IndexQuote[] }
export type WatchlistResponse = { symbols: string[]; quotes: Quote[]; provider: string; is_live: boolean }
export type Candle = {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  ema_20: number | null
  ema_50: number | null
  ema_200: number | null
  rsi_14: number | null
  macd: number | null
  macd_signal: number | null
  macd_histogram: number | null
}
