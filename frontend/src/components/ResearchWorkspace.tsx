import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { ResearchDocument } from '../types'

const categories = [
  ['annual_report', 'Annual report'],
  ['management_discussion', 'Management discussion & analysis'],
  ['earnings_transcript', 'Earnings-call transcript'],
  ['technical_chart', 'Technical chart'],
  ['financial_screener', 'Financial screener'],
  ['shareholding_pattern', 'Shareholding pattern'],
]
const labels = Object.fromEntries(categories)

export default function ResearchWorkspace() {
  const [documents, setDocuments] = useState<ResearchDocument[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [documentType, setDocumentType] = useState('annual_report')
  const [company, setCompany] = useState('')
  const [symbol, setSymbol] = useState('')
  const [period, setPeriod] = useState('')
  const [title, setTitle] = useState('')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<ResearchDocument[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function load() { const response = await api.researchDocuments(); setDocuments(response.documents) }
  useEffect(() => { void load().catch(e => setError(e.message)) }, [])

  async function upload(event: React.FormEvent) {
    event.preventDefault()
    if (!file) { setError('Choose a PDF first'); return }
    setBusy(true); setError(''); setMessage('')
    const form = new FormData()
    form.append('file', file); form.append('document_type', documentType)
    form.append('company_name', company)
    if (symbol) form.append('symbol', symbol)
    if (period) form.append('reporting_period', period)
    if (title) form.append('title', title)
    try {
      const doc = await api.uploadResearch(form)
      setMessage(`Uploaded “${doc.title}” — ${doc.page_count} pages indexed for text search.`)
      setFile(null); setTitle(''); await load()
      const input = document.getElementById('research-pdf') as HTMLInputElement | null
      if (input) input.value = ''
    } catch (e) { setError(e instanceof Error ? e.message : 'Upload failed') }
    finally { setBusy(false) }
  }

  async function search(event: React.FormEvent) {
    event.preventDefault(); setError('')
    if (query.trim().length < 2) return
    try { const response = await api.searchResearch(query.trim(), symbol || undefined); setResults(response.results) }
    catch (e) { setError(e instanceof Error ? e.message : 'Search failed') }
  }

  const shown = results ?? documents
  return <section className="section research-section">
    <div className="section-heading"><div><h2>Company research library</h2><p>Upload source documents and search their extracted text</p></div><span className="paper-tag">PHASE 2 · INGESTION</span></div>
    <div className="research-layout">
      <form className="panel research-upload" onSubmit={upload}>
        <div className="paper-form-title">Add research document</div>
        <label>PDF file<input id="research-pdf" type="file" accept="application/pdf,.pdf" onChange={e => setFile(e.target.files?.[0] || null)} required/></label>
        <label>Document type<select value={documentType} onChange={e => setDocumentType(e.target.value)}>{categories.map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label>Company name<input value={company} onChange={e => setCompany(e.target.value)} placeholder="e.g. Reliance Industries" required maxLength={160}/></label>
        <div className="research-two-col"><label>NSE symbol<input value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} placeholder="RELIANCE" maxLength={32}/></label><label>Reporting period<input value={period} onChange={e => setPeriod(e.target.value)} placeholder="FY 2025-26"/></label></div>
        <label>Display title (optional)<input value={title} onChange={e => setTitle(e.target.value)} placeholder="Annual report FY26"/></label>
        <button className="paper-submit" disabled={busy || !file || !company.trim()}>{busy ? 'Extracting PDF…' : 'Upload and extract text'}</button>
        <p className="paper-disclaimer">PDF only · 20 MB maximum · Text-based PDFs only for now. Scanned documents requiring OCR are not supported yet. Duplicate files are detected by SHA-256.</p>
        {message && <div className="paper-success">{message}</div>}{error && <div className="paper-error">{error}</div>}
      </form>
      <div className="panel research-library">
        <div className="research-library-head"><div><div className="paper-form-title">Research documents</div><div className="muted small">{documents.length} stored documents</div></div><button className="text-button" type="button" onClick={() => { setResults(null); setQuery('') }}>Show all</button></div>
        <form className="research-search" onSubmit={search}><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search extracted text, e.g. revenue growth…"/><button type="submit" disabled={query.trim().length < 2}>Search</button></form>
        <div className="research-doc-list">
          {shown.length ? shown.map(doc => <article className="research-doc" key={doc.id}><div className="research-doc-top"><strong>{doc.title}</strong><span className="research-doc-type">{labels[doc.document_type] || doc.document_type}</span></div><div className="research-doc-meta">{doc.company_name}{doc.symbol ? ` · ${doc.symbol}` : ''}{doc.reporting_period ? ` · ${doc.reporting_period}` : ''} · {doc.page_count} pages · {(doc.file_size / 1024 / 1024).toFixed(1)} MB</div>{doc.snippet && <p className="research-snippet">{doc.snippet}</p>}</article>) : <div className="paper-empty">{results ? 'No matching documents found.' : 'Your research library is empty. Upload a PDF to begin.'}</div>}
        </div>
      </div>
    </div>
  </section>
}
