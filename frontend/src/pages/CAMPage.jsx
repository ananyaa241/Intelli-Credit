import { useState } from 'react'
import { FileText, Download, Eye, CheckCircle, AlertTriangle } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { downloadCAM, getRecommendation } from '../api'

export default function CAMPage() {
    const { sessionId, companyName, recommendation } = useApp()
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [lookupId, setLookupId] = useState('')
    const [lookupResult, setLookupResult] = useState(null)

    const handleDownload = async (sid) => {
        const id = sid || sessionId
        if (!id) return setError('No active session. Run the recommendation first.')
        setLoading(true); setError('')
        try {
            const { data } = await downloadCAM(id)
            const url = URL.createObjectURL(new Blob([data], { type: 'application/pdf' }))
            const a = document.createElement('a')
            a.href = url
            a.download = `CAM_${companyName || id}_${new Date().toISOString().slice(0, 10)}.pdf`
            a.click()
            URL.revokeObjectURL(url)
        } catch {
            setError('CAM not available. Generate a recommendation first.')
        } finally {
            setLoading(false)
        }
    }

    const handleLookup = async () => {
        if (!lookupId) return
        try {
            const { data } = await getRecommendation(lookupId)
            setLookupResult(data)
        } catch {
            setError('Session not found.')
        }
    }

    const rec = lookupResult || recommendation
    const activeSession = lookupResult?.session_id || sessionId

    return (
        <div className="page">
            <div className="page-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                    <span className="tag tag-cyan">Step 4</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>CAM Report</span>
                </div>
                <h1 className="page-title">Credit Appraisal Memo</h1>
                <p className="page-subtitle">
                    Download the professional, bank-grade CAM PDF report or review session details.
                </p>
            </div>

            {/* Download Card */}
            <div className="card-grid card-grid-2" style={{ marginBottom: 24 }}>
                <div className="card" style={{
                    background: 'linear-gradient(135deg, rgba(13,27,75,0.8), rgba(22,36,102,0.8))',
                    borderColor: 'rgba(200,168,75,0.3)',
                    position: 'relative', overflow: 'hidden',
                }}>
                    <div style={{
                        position: 'absolute', top: -40, right: -40,
                        width: 160, height: 160, borderRadius: '50%',
                        background: 'radial-gradient(circle, rgba(200,168,75,0.1) 0%, transparent 70%)',
                    }} />
                    <div style={{ marginBottom: 16 }}>
                        <FileText size={40} style={{ color: 'var(--gold)' }} />
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
                        Credit Appraisal Memo — Full Report
                    </div>
                    <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginBottom: 20, lineHeight: 1.7 }}>
                        Professional A4 PDF including Five-Cs analysis, financials, risk matrix,
                        research signals, loan terms, and decision rationale.
                    </div>

                    {error && (
                        <div className="risk-flag high" style={{ marginBottom: 12 }}>
                            <AlertTriangle size={14} /> {error}
                        </div>
                    )}

                    <div style={{ display: 'flex', gap: 10 }}>
                        <button
                            className="btn btn-primary btn-lg"
                            onClick={() => handleDownload()}
                            disabled={loading || !sessionId}
                            id="download-cam-btn"
                        >
                            {loading ? <><span className="spinner" /> Preparing PDF…</> : <><Download size={16} /> Download CAM PDF</>}
                        </button>
                    </div>

                    {!sessionId && (
                        <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)' }}>
                            Complete Steps 1–3 to generate your CAM report.
                        </div>
                    )}
                </div>

                {/* Session lookup */}
                <div className="card">
                    <div className="card-title"><Eye size={14} /> Load by Session ID</div>
                    <div className="form-group">
                        <label className="form-label">Session ID</label>
                        <input
                            className="form-input"
                            placeholder="Paste session UUID here"
                            value={lookupId}
                            onChange={e => setLookupId(e.target.value)}
                            id="session-id-lookup-input"
                        />
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <button className="btn btn-secondary w-full" onClick={handleLookup} id="lookup-session-btn">
                            <Eye size={14} /> Load Session
                        </button>
                        {lookupResult && (
                            <button className="btn btn-primary" onClick={() => handleDownload(lookupResult.session_id)} id="download-lookup-cam-btn">
                                <Download size={14} />
                            </button>
                        )}
                    </div>

                    {sessionId && (
                        <div style={{ marginTop: 16, padding: 12, background: 'var(--bg-glass)', borderRadius: 'var(--radius-sm)' }}>
                            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>ACTIVE SESSION</div>
                            <div style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--accent-cyan)', wordBreak: 'break-all' }}>
                                {sessionId}
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>{companyName}</div>
                        </div>
                    )}
                </div>
            </div>

            {/* Recommendation Summary */}
            {rec && (
                <div>
                    <div className="section-divider" />
                    <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 16 }}>
                        Session Summary — {rec.session_id?.slice(0, 8)}…
                    </div>

                    <div className="card-grid card-grid-4" style={{ marginBottom: 20 }}>
                        {[
                            { label: 'Decision', value: rec.decision?.replace('_', ' '), color: rec.decision === 'APPROVE' ? 'var(--accent-green)' : rec.decision === 'REJECT' ? 'var(--accent-red)' : 'var(--gold)' },
                            { label: 'Credit Grade', value: rec.five_c_scores?.grade, color: 'var(--accent-cyan)' },
                            { label: 'Total Score', value: `${rec.five_c_scores?.total?.toFixed(0)}/100`, color: 'var(--text-primary)' },
                            { label: 'Risk Premium', value: `${rec.risk_premium_bps} bps`, color: 'var(--accent-orange)' },
                        ].map(({ label, value, color }) => (
                            <div key={label} className="stat-card">
                                <div className="stat-card-label">{label}</div>
                                <div className="stat-card-value" style={{ fontSize: 20, color }}>{value}</div>
                            </div>
                        ))}
                    </div>

                    {/* Five Cs table */}
                    <div className="card" style={{ marginBottom: 16 }}>
                        <div className="card-title">Five-Cs Scoring Matrix</div>
                        <table className="ic-table">
                            <thead>
                                <tr>
                                    <th>Pillar</th>
                                    <th>Score</th>
                                    <th>Weight</th>
                                    <th>Weighted</th>
                                    <th>Grade</th>
                                    <th>Bar</th>
                                </tr>
                            </thead>
                            <tbody>
                                {['character', 'capacity', 'capital', 'collateral', 'conditions'].map(c => {
                                    const sc = rec.five_c_scores?.[c] || 0
                                    const wts = { character: 0.25, capacity: 0.30, capital: 0.20, collateral: 0.15, conditions: 0.10 }
                                    const w = wts[c]
                                    const grade = sc >= 85 ? 'AAA' : sc >= 75 ? 'AA' : sc >= 65 ? 'A' : sc >= 55 ? 'BBB' : sc >= 45 ? 'BB' : 'B'
                                    return (
                                        <tr key={c}>
                                            <td style={{ fontWeight: 600 }}>{c.charAt(0).toUpperCase() + c.slice(1)}</td>
                                            <td style={{ color: FIVE_C_COLORS[c], fontWeight: 700 }}>{sc.toFixed(1)}</td>
                                            <td style={{ color: 'var(--text-muted)' }}>{(w * 100).toFixed(0)}%</td>
                                            <td>{(sc * w).toFixed(1)}</td>
                                            <td><span className="tag" style={{ background: `${FIVE_C_COLORS[c]}20`, color: FIVE_C_COLORS[c] }}>{grade}</span></td>
                                            <td>
                                                <div style={{ width: '100%', height: 6, background: 'var(--border-glass)', borderRadius: 3 }}>
                                                    <div style={{ width: `${sc}%`, height: '100%', background: FIVE_C_COLORS[c], borderRadius: 3, transition: 'width 1s ease' }} />
                                                </div>
                                            </td>
                                        </tr>
                                    )
                                })}
                                <tr style={{ background: 'rgba(200,168,75,0.05)' }}>
                                    <td style={{ fontWeight: 700 }}>TOTAL</td>
                                    <td style={{ fontWeight: 700, color: 'var(--gold)' }}>{rec.five_c_scores?.total?.toFixed(1)}</td>
                                    <td>100%</td>
                                    <td style={{ fontWeight: 700 }}>{rec.five_c_scores?.total?.toFixed(1)}</td>
                                    <td><span className="tag tag-gold">{rec.five_c_scores?.grade}</span></td>
                                    <td>
                                        <div style={{ width: '100%', height: 6, background: 'var(--border-glass)', borderRadius: 3 }}>
                                            <div style={{ width: `${rec.five_c_scores?.total}%`, height: '100%', background: 'var(--grad-gold)', borderRadius: 3 }} />
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    {/* Rationale */}
                    {rec.decision_rationale && (
                        <div className="card">
                            <div className="card-title"><CheckCircle size={14} /> AI Rationale</div>
                            <p style={{ fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                                {rec.decision_rationale}
                            </p>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

const FIVE_C_COLORS = {
    character: '#C8A84B',
    capacity: '#00D4FF',
    capital: '#00E5A0',
    collateral: '#FF8C42',
    conditions: '#A78BFA',
}
