import { useEffect, useState } from 'react'
import { Activity, ArrowDownRight, ArrowUpRight, Bell, ChartNoAxesCombined, CircleDollarSign, RefreshCw, Search, ShieldCheck } from 'lucide-react'
import { api } from '../services/api'
import type { Overview, Signal, WatchlistResponse, KiteAuthStatus, StockIntelligence } from '../types'
import { MetricCard } from '../components/MetricCard'
import { SignalTable } from '../components/SignalTable'
import StockChart from '../components/StockChart'
import PaperTrading from '../components/PaperTrading'

const inr = (n: number) => `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`

export default function Dashboard() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [watchlist, setWatchlist] = useState<WatchlistResponse | null>(null)
  const [signals, setSignals] = useState<Signal[]>([])
  const [intelligence, setIntelligence] = useState<StockIntelligence | null>(null)
  const [intelligenceLoading, setIntelligenceLoading] = useState(false)
  const [intelligenceError, setIntelligenceError] = useState('')
  const [account, setAccount] = useState<{ starting_cash: number; cash_balance: number; invested_value: number; unrealized_pnl: number; mode: string } | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [streamStatus, setStreamStatus] = useState('Connecting market stream…')
  const [kiteAuth, setKiteAuth] = useState<KiteAuthStatus | null>(null)
  const [selectedSymbol, setSelectedSymbol] = useState('RELIANCE')
  const [tradeIntent, setTradeIntent] = useState<{ symbol: string; side: 'BUY' | 'SELL'; id: number } | null>(null)
  const [watchlistInput, setWatchlistInput] = useState('')
  const [watchlistBusy, setWatchlistBusy] = useState(false)
  const [watchlistMessage, setWatchlistMessage] = useState('')
  const [instrumentSuggestions, setInstrumentSuggestions] = useState<import('../types').InstrumentSuggestion[]>([])
  const [suggestionsOpen, setSuggestionsOpen] = useState(false)
  const todayLabel = new Date().toLocaleDateString('en-IN', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }).toUpperCase()

  useEffect(() => {
    const query = watchlistInput.trim()
    if (query.length < 1) { setInstrumentSuggestions([]); return }
    let cancelled = false
    const timer = window.setTimeout(() => {
      void api.searchInstruments(query).then(response => {
        if (!cancelled) setInstrumentSuggestions(response.results.filter(item => !(watchlist?.symbols || []).includes(item.symbol)))
      }).catch(() => { if (!cancelled) setInstrumentSuggestions([]) })
    }, 250)
    return () => { cancelled = true; window.clearTimeout(timer) }
  }, [watchlistInput, watchlist?.symbols.join(',')])

  async function generateIntelligence() {
    setIntelligenceLoading(true)
    setIntelligenceError('')
    setIntelligence(null)
    try {
      setIntelligence(await api.stockIntelligence(selectedSymbol))
    } catch (e) {
      setIntelligenceError(e instanceof Error ? e.message : 'Could not generate AI analysis')
    } finally {
      setIntelligenceLoading(false)
    }
  }

  async function manageWatchlist(action: 'add' | 'remove', symbol: string) {
    setWatchlistBusy(true)
    setWatchlistMessage('')
    try {
      if (action === 'add') await api.addWatchlistSymbol(symbol)
      else await api.removeWatchlistSymbol(symbol)
      const [next, signalResponse] = await Promise.all([api.watchlist(), api.signals()])
      setWatchlist(next)
      setSignals(signalResponse.signals)
      if (action === 'add') {
        setSelectedSymbol(symbol)
        setWatchlistInput('')
        setInstrumentSuggestions([])
        setSuggestionsOpen(false)
        setWatchlistMessage(symbol + ' added to watchlist')
      } else {
        if (selectedSymbol === symbol) setSelectedSymbol(next.symbols[0] || 'RELIANCE')
        setWatchlistMessage(symbol + ' removed from watchlist')
      }
    } catch (e) {
      setWatchlistMessage(e instanceof Error ? e.message : 'Could not update watchlist')
    } finally {
      setWatchlistBusy(false)
    }
  }

  useEffect(() => {
    setIntelligence(null)
    setIntelligenceError('')
  }, [selectedSymbol])

  async function refresh() {
    setLoading(true); setError('')
    try {
      const [o, w, s, a, k] = await Promise.all([api.overview(), api.watchlist(), api.signals(), api.account(), api.kiteAuthStatus()])
      setOverview(o); setWatchlist(w); setSignals(s.signals); setAccount(a); setKiteAuth(k)
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to connect to DhanSignal API') }
    finally { setLoading(false) }
  }
  useEffect(() => {
    void refresh()
    const id = window.setInterval(() => void refresh(), 60_000)
    return () => window.clearInterval(id)
  }, [])
  useEffect(() => {
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
    const wsUrl = apiBase.replace('http://', 'ws://').replace('https://', 'wss://').replace('/api/v1', '') + '/api/v1/market/stream'
    let socket: WebSocket | null = null
    let retry: number | undefined
    let stopped = false
    const connect = () => {
      socket = new WebSocket(wsUrl)
      socket.onopen = () => setStreamStatus('Market stream connected')
      socket.onmessage = event => {
        const message = JSON.parse(event.data) as { type: string; provider?: string; is_live?: boolean; data?: WatchlistResponse['quotes'] }
        if (message.data?.length) setWatchlist(previous => previous ? {
          ...previous,
          // Keep quotes for watchlist symbols not included in a partial stream snapshot.
          quotes: Array.from(new Map([...previous.quotes, ...message.data!].map(quote => [quote.symbol, quote])).values()),
          provider: message.provider || previous.provider,
          is_live: message.is_live ?? previous.is_live,
        } : previous)
        if (message.provider) setStreamStatus(message.provider === 'ZERODHA KITE CONNECT' ? message.provider + (message.is_live ? ' · STREAM LIVE' : ' · STREAM DISCONNECTED') : message.provider === 'DEMO DATA' ? message.provider + ' · SYNTHETIC PRICES' : message.provider + ' · REST / DELAYED SNAPSHOTS')
      }
      socket.onerror = () => setStreamStatus('Market stream reconnecting…')
      socket.onclose = () => { if (!stopped) retry = window.setTimeout(connect, 3000) }
    }
    connect()
    return () => { stopped = true; if (retry) window.clearTimeout(retry); socket?.close() }
  }, [])
  useEffect(() => {
    const id = window.setInterval(() => { void api.signals().then(response => setSignals(response.signals)).catch(() => undefined) }, 15_000)
    return () => window.clearInterval(id)
  }, [])

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><img src="/dhansignal.svg" alt="DhanSignal logo"/></div><div><strong>DhanSignal</strong><span>MARKET INTELLIGENCE</span></div></div>
      <div className="nav-label">WORKSPACE</div>
      <a className="nav-item active" href="#overview"><Activity size={18}/> Overview</a><a className="nav-item" href="#signals"><ChartNoAxesCombined size={18}/> Signals</a><a className="nav-item" href="#portfolio"><CircleDollarSign size={18}/> Portfolio</a>
      <div className="nav-label second">PAPER TRADING</div><a className="nav-item" href="#simulator"><CircleDollarSign size={18}/> Simulator</a><a className="nav-item" href="#journal"><Activity size={18}/> Trade journal</a>
      <div className="sidebar-bottom"><div className="secure"><ShieldCheck size={16}/><span>Broker credentials stay<br/>on your backend</span></div><div className="user"><div className="avatar">D</div><div><strong>Personal workspace</strong><span>Free development mode</span></div></div></div>
    </aside>
    <main className="main-content" id="overview">
      <header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <strong>Overview</strong></div><div className="top-actions"><div className="market-clock"><span className="live-dot"/> NSE MARKET DATA</div><button className="icon-button" aria-label="Search"><Search size={18}/></button><button className="icon-button" aria-label="Notifications"><Bell size={18}/></button><button className="refresh-button" onClick={() => void refresh()}><RefreshCw size={15}/> Refresh</button></div></header>
      <section className="page-heading"><div><div className="eyebrow">{todayLabel}</div><h1>Market overview</h1><p>Your trading cockpit for the Indian equity markets.</p></div><div className="heading-right"><span className={`provider-tag ${overview?.is_live ? 'live' : 'demo'}`}><span/> {overview?.provider || 'CONNECTING...'}</span><span className="muted small">{overview?.is_live ? 'Live provider' : overview?.provider === 'DEMO DATA' ? 'Synthetic demo feed' : overview?.provider === 'ZERODHA KITE CONNECT' ? 'Login required for live data' : 'REST / historical data'}</span>{kiteAuth?.configured && !kiteAuth.authenticated && <a className="refresh-button" href={(import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '') + '/api/v1/auth/zerodha/login'}>Connect Zerodha</a>}</div></section>
      {error && <div className="error-banner">{error}. Start the API and database with <code>docker compose up --build</code>.</div>}
      {overview?.provider === 'DEMO DATA' && <div className="demo-banner"><Activity size={17}/><span><strong>Demo mode active.</strong> Prices and signals are synthetic placeholders, not NSE/BSE quotes. Configure Kite credentials to use your authorized market feed.</span></div>}
      <section className="section"><div className="section-heading"><div><h2>Market pulse</h2><p>Index snapshots from the configured provider</p></div><span className="muted small">{loading ? 'Updating…' : streamStatus}</span></div><div className="metric-grid">{(overview?.indices || [{symbol:'NIFTY 50',last_price:0,change_percent:0},{symbol:'SENSEX',last_price:0,change_percent:0}]).map(index => <div className="index-card" key={index.symbol}><div className="index-top"><span>{index.symbol}</span><span className={index.change_percent >= 0 ? 'trend-up' : 'trend-down'}>{index.change_percent >= 0 ? <ArrowUpRight size={15}/> : <ArrowDownRight size={15}/>}{index.change_percent.toFixed(2)}%</span></div><div className="index-value">{index.last_price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div><div className="sparkline"><span style={{width:`${Math.max(12, Math.min(100, 50 + index.change_percent * 12))}%`}}/></div></div>)}</div></section>
      <StockChart quotes={watchlist?.quotes || []} symbols={watchlist?.symbols || []} selectedSymbol={selectedSymbol} onSymbolChange={setSelectedSymbol} />
      <section className="section intelligence-section" id="intelligence">
        <div className="section-heading"><div><h2>Gemini stock intelligence</h2><p>AI interpretation grounded in the selected stock's market snapshot and technical indicators</p></div><button className="intelligence-button" onClick={() => void generateIntelligence()} disabled={intelligenceLoading || !selectedSymbol}>{intelligenceLoading ? 'Analysing…' : intelligence ? 'Refresh analysis' : 'Analyse ' + selectedSymbol}</button></div>
        {intelligenceError && <div className="intelligence-error" role="alert">{intelligenceError}</div>}
        {intelligence && <div className="panel intelligence-panel">
          <div className="intelligence-top"><div><span className="intelligence-symbol">{intelligence.symbol}</span><span className="intelligence-meta">{intelligence.model} · {intelligence.provider}{intelligence.cached ? ' · cached' : ''}</span></div><div className="intelligence-tags"><span className={'intelligence-stance ' + intelligence.analysis.final_verdict.rating.toLowerCase()}>{intelligence.analysis.final_verdict.rating}</span><span className="intelligence-confidence">{intelligence.analysis.final_verdict.conviction_score}/10 CONVICTION</span></div></div>
          <p className="intelligence-summary">{intelligence.analysis.final_verdict.one_line_summary}</p>
          <div className="intelligence-grid">{[['Fundamentals', intelligence.analysis.fundamentals], ['Management DNA', intelligence.analysis.management_dna], ['Valuation Reality', intelligence.analysis.valuation_reality], ['Technical Structure', intelligence.analysis.technical_structure]].map(([label, value]) => <div className="intelligence-item" key={label}><strong>{label}</strong><p>{value}</p></div>)}</div>
          <div className="intelligence-lists"><div><strong>Risk factors</strong><ul>{intelligence.analysis.risk_factors?.map((item, i) => <li key={i}>{item}</li>)}</ul></div><div><strong>Key evidence</strong><ul>{intelligence.analysis.key_evidence?.map((item, i) => <li key={i}>{item}</li>)}</ul></div></div>
          <div className="intelligence-item"><strong>Interesting entry price</strong><p>{intelligence.analysis.final_verdict.interesting_price == null ? 'Not enough evidence to derive a level' : inr(intelligence.analysis.final_verdict.interesting_price)}</p></div>
          {intelligence.analysis.data_gaps?.length > 0 && <div className="intelligence-caveats"><strong>Data unavailable / gaps</strong><ul>{intelligence.analysis.data_gaps.map((item, i) => <li key={i}>{item}</li>)}</ul></div>}
          {intelligence.analysis.caveats?.length > 0 && <div className="intelligence-caveats"><strong>Caveats</strong><ul>{intelligence.analysis.caveats.map((item, i) => <li key={i}>{item}</li>)}</ul></div>}
          {intelligence.sources?.length > 0 && <div className="intelligence-caveats"><strong>Web sources reviewed</strong><ul>{intelligence.sources.map(source => <li key={source.url}><a href={source.url} target="_blank" rel="noreferrer">{source.title || source.url}</a></li>)}</ul></div>}
          {intelligence.search_queries?.length > 0 && <details className="intelligence-caveats"><summary>Search queries used</summary><ul>{intelligence.search_queries.map((query, i) => <li key={i}>{query}</li>)}</ul></details>}
          <div className="intelligence-disclaimer">{intelligence.disclaimer} Generated {new Date(intelligence.generated_at).toLocaleString('en-IN')}.</div>
        </div>}
        {!intelligence && !intelligenceError && !intelligenceLoading && <div className="intelligence-empty">Select a stock in the chart selector, then generate a Gemini-powered technical and risk assessment. Your Gemini API key stays on the backend.</div>}
      </section>
      <section className="section" id="portfolio"><div className="section-heading"><div><h2>Paper trading account</h2><p>Virtual capital · No real orders are placed</p></div><span className="paper-tag">PAPER MODE</span></div><div className="account-grid"><MetricCard label="Starting capital" value={inr(account?.starting_cash ?? 100000)} change="Virtual allocation" positive/><MetricCard label="Available cash" value={inr(account?.cash_balance ?? 100000)} change="Ready to deploy" positive/><MetricCard label="Invested value" value={inr(account?.invested_value ?? 0)} change="No open positions"/><MetricCard label="Unrealized P&L" value={inr(account?.unrealized_pnl ?? 0)} change="After simulated fills"/></div></section>
      {/* Research document upload is parked while live trading is built. */}
      <div id="simulator"><PaperTrading symbols={watchlist?.symbols || ['RELIANCE', 'HDFCBANK', 'INFY', 'ICICIBANK', 'TCS', 'LT']} liveQuotes={watchlist?.quotes || []} selectedSymbol={selectedSymbol} tradeIntent={tradeIntent} /></div>
      <section className="section" id="signals"><div className="section-heading"><div><h2>AI-assisted trade signals</h2><p>Experimental strategy v0.2 · EMA, RSI, MACD, volume and ATR</p></div><span className="muted small">Strategy v0.2</span></div><div className="panel"><SignalTable signals={signals} onPrepareTrade={symbol => { setSelectedSymbol(symbol); setTradeIntent({ symbol, side: 'BUY', id: Date.now() }); document.getElementById('simulator')?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }} /><div className="panel-foot"><span>Signals are rule-based candidates, not personalized investment advice.</span><span>{signals.length} symbols scanned</span></div></div></section>
      <section className="section" id="watchlist"><div className="section-heading"><div><h2>Watchlist</h2><p>Starter NSE universe · Expandable from the scanner</p></div><form className="watchlist-manager" onSubmit={event => { event.preventDefault(); const value = watchlistInput.trim().toUpperCase(); if (value) void manageWatchlist('add', value) }}>
        <div className="watchlist-autocomplete">
          <input aria-label="Search NSE/BSE stocks" placeholder="Search stocks…" value={watchlistInput} onFocus={() => setSuggestionsOpen(true)} onChange={event => { setWatchlistInput(event.target.value.toUpperCase()); setSuggestionsOpen(true) }} maxLength={40} autoComplete="off"/>
          {suggestionsOpen && watchlistInput.trim() && <div className="watchlist-suggestions" role="listbox">
            {instrumentSuggestions.length ? instrumentSuggestions.map(item => <button type="button" key={item.exchange + item.symbol} role="option" className="watchlist-suggestion" onClick={() => { setWatchlistInput(item.symbol); setSuggestionsOpen(false); void manageWatchlist('add', item.symbol) }}><span><strong>{item.symbol}</strong><small>{item.name}</small></span><em>{item.exchange}</em></button>) : <div className="watchlist-no-suggestions">Searching NSE/BSE instruments…</div>}
          </div>}
        </div>
        <button type="submit" disabled={watchlistBusy || !watchlistInput.trim()}>+ Add</button>
      </form></div><div className="panel watch-panel">{watchlistMessage && <div className="watchlist-feedback" role="status">{watchlistMessage}</div>}<div className="watch-head"><span>INSTRUMENT</span><span>LAST TRADED PRICE</span><span>DAY CHANGE</span><span>VOLUME</span></div>{(watchlist?.symbols || []).map(symbol => {
        const q = watchlist?.quotes.find(quote => quote.symbol === symbol)
        return <div className="watch-row" key={symbol}><button type="button" className="watch-name watch-select" onClick={() => { setSelectedSymbol(symbol); document.getElementById("chart")?.scrollIntoView({ behavior: "smooth" }) }}><span className="stock-icon">{symbol.slice(0,1)}</span><span><strong>{symbol}</strong><small>NSE · EQ · View chart</small></span></button><strong>{q ? inr(q.last_price) : '—'}</strong><span className={q ? (q.change_percent >= 0 ? 'trend-up' : 'trend-down') : 'muted'}>{q ? `${q.change_percent >= 0 ? '+' : ''}${q.change_percent.toFixed(2)}%` : 'Quote unavailable'}</span><span className="muted">{q ? q.volume.toLocaleString('en-IN') : '—'}</span><button type="button" className="watch-remove" aria-label={`Remove ${symbol} from watchlist`} title="Remove from watchlist" disabled={watchlistBusy || (watchlist?.symbols.length || 0) <= 1} onClick={() => void manageWatchlist('remove', symbol)}>×</button></div>
      })}</div></section>
      <footer><span>DhanSignal v0.1.0</span><span>Market data: {overview?.provider || 'Not connected'} · For research and simulation only</span></footer>
    </main>
  </div>
}
