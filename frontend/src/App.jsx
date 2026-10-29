import { useEffect, useState } from 'react'

const API = 'http://127.0.0.1:8000/api'
const examples = ['What is the total net revenue?', 'Which product has the highest revenue?', 'Show monthly revenue trend', 'Which region has highest revenue?', 'Compare revenue between 2026-01 and 2026-06']
const money = value => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value || 0)

export default function App() {
  const [summary, setSummary] = useState(null)
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  useEffect(() => { fetch(`${API}/summary`).then(r => { if (!r.ok) throw Error('Could not reach the backend. Start FastAPI and refresh.'); return r.json() }).then(setSummary).catch(e => setError(e.message)) }, [])
  async function ask(value = question) {
    setLoading(true); setError(''); setResult(null)
    try { const response = await fetch(`${API}/question`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: value }) }); const data = await response.json(); if (!response.ok) throw Error(data.detail || 'Request failed'); setResult(data) }
    catch (e) { setError(e.message) } finally { setLoading(false) }
  }
  const max = Math.max(1, ...(summary?.monthly_trend || []).map(m => m.revenue))
  return <main className="shell"><header><div className="brand-mark">BI</div><div><p className="eyebrow">SALES INTELLIGENCE</p><h1>Business, made clear.</h1></div><span className="live"><i/> Local data</span></header>
    <section className="hero"><div><p className="eyebrow">ASK YOUR SALES DATA</p><h2>What would you like to know?</h2><p className="muted">Ask a question in plain language. Answers are calculated from your sales records.</p></div>
      <form onSubmit={e => { e.preventDefault(); ask() }}><label htmlFor="question">Your question</label><div className="input-row"><input id="question" value={question} onChange={e => setQuestion(e.target.value)} placeholder="e.g. Which region had the most net revenue?"/><button disabled={loading || !question.trim()}>{loading ? 'Thinking…' : 'Ask'} <span aria-hidden="true">↗</span></button></div></form>
      <div className="examples" aria-label="Example questions">{examples.map(item => <button key={item} className="chip" onClick={() => { setQuestion(item); ask(item) }}>{item}</button>)}</div>
    </section>
    {error && <div className="error" role="alert">{error}</div>}
    {result && <section className="answer"><div className="answer-icon">✦</div><div><p className="eyebrow">{result.source === 'gemini' ? 'GEMINI INTERPRETATION' : 'DETERMINISTIC ANSWER'}</p><h3>{result.answer}</h3>{result.figures.monthly_trend && <div className="mini-list">{result.figures.monthly_trend.map(m => <span key={m.month}>{m.month}: {money(m.revenue)}</span>)}</div>}{result.figures.percentage_change !== undefined && <p className="muted">{result.figures.start_month}: {money(result.figures.start_revenue)} · {result.figures.end_month}: {money(result.figures.end_revenue)} · Change: {result.figures.percentage_change === null ? 'not defined from a zero baseline' : `${result.figures.percentage_change}%`}</p>}</div></section>}
    <section className="stats"><article className="stat"><span className="stat-label">TOTAL NET REVENUE</span><strong>{summary ? money(summary.total_revenue) : '—'}</strong><small>Eligible completed sales</small></article><article className="stat"><span className="stat-label">TOP PRODUCT</span><strong>{summary?.top_product?.product || '—'}</strong><small>{summary ? money(summary.top_product?.revenue) : 'Loading'}</small></article><article className="stat"><span className="stat-label">LEADING REGION</span><strong>{summary?.top_region?.region || '—'}</strong><small>{summary ? money(summary.top_region?.revenue) : 'Loading'}</small></article><article className="stat"><span className="stat-label">RECORDS INCLUDED</span><strong>{summary ? `${summary.records.eligible} / ${summary.records.imported}` : '—'}</strong><small>{summary?.records.excluded ?? '—'} excluded from revenue</small></article></section>
    <section className="panel"><div className="panel-heading"><div><p className="eyebrow">PERFORMANCE</p><h2>Monthly net revenue</h2></div><span className="unit">INR</span></div><div className="chart" role="img" aria-label="Monthly net revenue bar chart">{summary?.monthly_trend.map(m => <div className="bar-column" key={m.month} title={`${m.month}: ${money(m.revenue)}`}><span className="bar-value">{money(m.revenue)}</span><div className="bar" style={{ height: `${Math.max(4, m.revenue / max * 100)}%` }}/><span className="bar-label">{m.month}</span></div>)}</div></section>
    <footer><span>Revenue = quantity × unit price − discount</span><span>Returns and invalid records are excluded.</span></footer></main>
}
