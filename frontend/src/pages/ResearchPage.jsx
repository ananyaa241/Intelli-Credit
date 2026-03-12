import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Globe, User, Newspaper, Scale, AlertTriangle, ChevronRight, CheckCircle, Plus, X } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { runResearch } from '../api'

export default function ResearchPage() {
    const navigate = useNavigate()
    const { sessionId, companyName: globalName, setResearchData, addToast } = useApp()

    const [company, setCompany] = useState(globalName || '')
    const [sector, setSector] = useState('')
    const [promoters, setPromoters] = useState([''])
    const [qualNotes, setQualNotes] = useState('')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState(null)
    const [activeSection, setActiveSection] = useState('company')

    const addPromoter = () => setPromoters(prev => [...prev, ''])
    const removePromoter = (i) => setPromoters(prev => prev.filter((_, idx) => idx !== i))
    const updatePromoter = (i, val) => setPromoters(prev => prev.map((p, idx) => idx === i ? val : p))

    const handleRun = async () => {
        if (!company.trim()) return addToast('Enter a company name.', 'error')
        if (!sessionId) addToast('No active session. Upload documents first for full analysis.', 'info')

        setLoading(true)
        const payload = {
            session_id: sessionId || 'standalone',
            company_name: company,
            promoter_names: promoters.filter(Boolean),
            sector,
            qualitative_notes: qualNotes,
        }
        try {
            const { data } = await runResearch(payload)
            setResult(data)
            setResearchData(data)
            addToast('Research complete!', 'success')
        } catch (err) {
            addToast(err?.response?.data?.detail || 'Research failed.', 'error')
        } finally {
            setLoading(false)
        }
    }

    const NewsCard = ({ item }) => (
        <div className="news-card">
            <div className="news-card-title">{item.title || 'No title'}</div>
            <div className="news-card-snippet">{item.snippet || '—'}</div>
            {item.link && (
                <a href={item.link} target="_blank" rel="noopener noreferrer" className="news-card-link">
                    Read more →
                </a>
            )}
            {item.date && <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>{item.date}</div>}
        </div>
    )

    const sections = result ? [
        { id: 'company', label: 'Company News', icon: Newspaper, data: result.company_news },
        { id: 'promoter', label: 'Promoter Checks', icon: User, data: result.promoter_background },
        { id: 'sector', label: 'Sector Headwinds', icon: Globe, data: result.sector_headwinds },
        { id: 'litigation', label: 'Litigation', icon: Scale, data: result.litigation_history },
        { id: 'regulatory', label: 'Regulatory', icon: AlertTriangle, data: result.regulatory_updates },
    ] : []

    return (
        <div className="page">
            <div className="page-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                    <span className="tag tag-gold">Step 2</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>Research Agent</span>
                </div>
                <h1 className="page-title">Digital Credit Manager</h1>
                <p className="page-subtitle">
                    Web-scale secondary research on company news, promoter integrity, sector headwinds, and litigation history.
                </p>
            </div>

            <div className="card-grid card-grid-2" style={{ marginBottom: 24 }}>
                {/* Input form */}
                <div>
                    <div className="card">
                        <div className="form-group">
                            <label className="form-label">Company Name *</label>
                            <input className="form-input" value={company} onChange={e => setCompany(e.target.value)}
                                placeholder="e.g. Adani Ports Ltd" id="research-company-input" />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Industry / Sector</label>
                            <input className="form-input" value={sector} onChange={e => setSector(e.target.value)}
                                placeholder="e.g. Infrastructure, NBFC, Real Estate" id="research-sector-input" />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Key Promoters / Directors</label>
                            {promoters.map((p, i) => (
                                <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
                                    <input
                                        className="form-input"
                                        placeholder={`Promoter ${i + 1} full name`}
                                        value={p}
                                        onChange={e => updatePromoter(i, e.target.value)}
                                        id={`promoter-input-${i}`}
                                    />
                                    {promoters.length > 1 && (
                                        <button className="btn btn-danger btn-sm" onClick={() => removePromoter(i)}>
                                            <X size={13} />
                                        </button>
                                    )}
                                </div>
                            ))}
                            <button className="btn btn-secondary btn-sm" onClick={addPromoter}>
                                <Plus size={13} /> Add Promoter
                            </button>
                        </div>

                        <button
                            className="btn btn-primary w-full"
                            style={{ marginTop: 4 }}
                            onClick={handleRun}
                            disabled={loading}
                            id="run-research-btn"
                        >
                            {loading
                                ? <><span className="spinner" /> Running Web Research…</>
                                : <><Search size={16} /> Run Research Agent</>
                            }
                        </button>
                    </div>
                </div>

                {/* Qualitative Notes */}
                <div className="card" style={{ background: 'rgba(200,168,75,0.03)', borderColor: 'rgba(200,168,75,0.2)' }}>
                    <div className="card-title">
                        👁 Primary Due Diligence Notes
                        <span className="tag tag-gold" style={{ marginLeft: 'auto', fontWeight: 500 }}>AI-Scored</span>
                    </div>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12, lineHeight: 1.6 }}>
                        Enter qualitative observations from factory visits, management interviews, or site inspections.
                        The AI adjusts the credit score based on these nuances.
                    </p>
                    <textarea
                        className="form-textarea"
                        style={{ minHeight: 200 }}
                        placeholder={`Examples:
• Factory found operating at only 40% capacity
• Management appeared evasive about FY23 revenue decline
• Collateral property is prime Mumbai commercial — good
• Working capital cycle appears stretched (120 days)
• Promoter has strong banking relationships with SBI`}
                        value={qualNotes}
                        onChange={e => setQualNotes(e.target.value)}
                        id="qual-notes-textarea"
                    />
                    {result?.qualitative_adjustment && (
                        <div style={{ marginTop: 12, padding: '12px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-sm)' }}>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>AI QUALITATIVE ADJUSTMENT</div>
                            <div style={{
                                fontSize: 20, fontWeight: 800,
                                color: result.qualitative_adjustment.score_adjustment >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
                            }}>
                                {result.qualitative_adjustment.score_adjustment >= 0 ? '+' : ''}
                                {result.qualitative_adjustment.score_adjustment} pts
                            </div>
                            {result.qualitative_adjustment.adjustment_reasons?.map((r, i) => (
                                <div key={i} style={{ fontSize: 11.5, color: 'var(--text-secondary)', marginTop: 4 }}>• {r}</div>
                            ))}
                            {result.qualitative_adjustment.critical_concerns?.map((c, i) => (
                                <div key={i} className="risk-flag high" style={{ marginTop: 6, fontSize: 11 }}>⚠ {c}</div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Results */}
            {result && (
                <div>
                    <div className="section-divider" />
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <CheckCircle size={20} style={{ color: 'var(--accent-green)' }} />
                            <span style={{ fontWeight: 700, fontSize: 15 }}>Research Complete</span>
                        </div>
                        <button className="btn btn-primary" onClick={() => navigate('/recommendation')} id="proceed-to-rec-btn">
                            Generate Recommendation <ChevronRight size={15} />
                        </button>
                    </div>

                    {/* Risk signals summary */}
                    {result.risk_signals?.length > 0 && (
                        <div className="card" style={{ marginBottom: 20, borderColor: 'rgba(255,71,87,0.3)' }}>
                            <div className="card-title" style={{ color: 'var(--accent-red)' }}>
                                <AlertTriangle size={14} /> Early Warning Signals Detected
                            </div>
                            {result.risk_signals.map((s, i) => (
                                <div key={i} className="risk-flag high">⚠ {s}</div>
                            ))}
                        </div>
                    )}

                    {/* Research summary */}
                    {result.research_summary && (
                        <div className="card" style={{ marginBottom: 20 }}>
                            <div className="card-title">📋 Research Summary</div>
                            <p style={{ fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                                {result.research_summary}
                            </p>
                        </div>
                    )}

                    {/* Section tabs */}
                    <div style={{ display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' }}>
                        {sections.map(({ id, label, icon: Icon, data }) => (
                            <button
                                key={id}
                                onClick={() => setActiveSection(id)}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 6,
                                    padding: '7px 14px',
                                    background: activeSection === id ? 'var(--gold-glow)' : 'var(--bg-glass)',
                                    border: `1px solid ${activeSection === id ? 'var(--border-gold)' : 'var(--border-glass)'}`,
                                    borderRadius: 'var(--radius-pill)',
                                    color: activeSection === id ? 'var(--gold)' : 'var(--text-muted)',
                                    fontSize: 12, fontWeight: 600, cursor: 'pointer',
                                }}
                            >
                                <Icon size={13} />
                                {label}
                                <span style={{ background: 'rgba(255,255,255,0.1)', padding: '1px 6px', borderRadius: 20, fontSize: 10 }}>
                                    {data?.length || 0}
                                </span>
                            </button>
                        ))}
                    </div>

                    <div style={{ display: 'grid', gap: 12 }}>
                        {sections.find(s => s.id === activeSection)?.data?.map((item, i) => (
                            <NewsCard key={i} item={item} />
                        ))}
                        {(sections.find(s => s.id === activeSection)?.data?.length === 0) && (
                            <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: 16 }}>No results found for this category.</div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
