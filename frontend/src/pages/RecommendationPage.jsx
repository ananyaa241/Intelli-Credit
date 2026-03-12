import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ShieldCheck, ChevronRight, AlertTriangle, TrendingUp, CheckCircle, X, Info } from 'lucide-react'
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, Cell } from 'recharts'
import { useApp } from '../context/AppContext'
import { generateRecommendation } from '../api'

const FIVE_C_COLORS = {
    character: '#C8A84B',
    capacity: '#00D4FF',
    capital: '#00E5A0',
    collateral: '#FF8C42',
    conditions: '#A78BFA',
}

function ScoreRing({ value, color, label }) {
    const r = 34, c = 2 * Math.PI * r
    const pct = Math.max(0, Math.min(100, value))
    const dash = (pct / 100) * c

    return (
        <div className="score-gauge">
            <div className="score-ring" style={{ width: 88, height: 88 }}>
                <svg viewBox="0 0 88 88" width="88" height="88" style={{ transform: 'rotate(-90deg)' }}>
                    <circle cx="44" cy="44" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="6" />
                    <circle
                        cx="44" cy="44" r={r} fill="none"
                        stroke={color} strokeWidth="6"
                        strokeDasharray={`${dash} ${c - dash}`}
                        strokeLinecap="round"
                        style={{ transition: 'stroke-dasharray 1s ease' }}
                    />
                </svg>
                <div className="score-ring-text" style={{ color, fontSize: 17 }}>{value.toFixed(0)}</div>
            </div>
            <div className="score-label" style={{ color }}>{label}</div>
        </div>
    )
}

export default function RecommendationPage() {
    const navigate = useNavigate()
    const { sessionId, companyName: globalName, setRecommendation: setGlobalRec, addToast } = useApp()

    const [company, setCompany] = useState(globalName || '')
    const [loanAmount, setLoanAmount] = useState('')
    const [loanPurpose, setLoanPurpose] = useState('')
    const [tenure, setTenure] = useState('60')
    const [collateral, setCollateral] = useState('')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState(null)

    const handleGenerate = async () => {
        if (!company.trim()) return addToast('Enter company name.', 'error')

        setLoading(true)
        const payload = {
            session_id: sessionId || 'standalone',
            company_name: company,
            loan_amount_requested: loanAmount ? parseFloat(loanAmount) : null,
            loan_purpose: loanPurpose,
            tenure_months: parseInt(tenure) || 60,
            collateral_value: collateral ? parseFloat(collateral) : null,
        }
        try {
            const { data } = await generateRecommendation(payload)
            setResult(data)
            setGlobalRec(data)
            addToast('Recommendation generated!', 'success')
        } catch (err) {
            addToast(err?.response?.data?.detail || 'Generation failed.', 'error')
        } finally {
            setLoading(false)
        }
    }

    const radarData = result
        ? Object.entries(result.five_c_scores).slice(0, 5).map(([key, val]) => ({
            subject: key.charAt(0).toUpperCase() + key.slice(1),
            score: val,
            fullMark: 100,
        }))
        : []

    const barData = result
        ? Object.entries(result.five_c_scores).slice(0, 5).map(([key, val]) => ({
            name: key.charAt(0).toUpperCase() + key.slice(1),
            score: val,
            color: FIVE_C_COLORS[key],
        }))
        : []

    const decisionClass = result?.decision === 'APPROVE'
        ? 'approve'
        : result?.decision === 'CONDITIONAL_APPROVE'
            ? 'conditional'
            : 'reject'

    return (
        <div className="page">
            <div className="page-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                    <span className="tag tag-green">Step 3</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>Recommendation Engine</span>
                </div>
                <h1 className="page-title">Credit Decision & Scoring</h1>
                <p className="page-subtitle">
                    Five-Cs scoring model with AI-powered rationale. Transparent, explainable credit decisions.
                </p>
            </div>

            {/* Form */}
            <div className="card" style={{ marginBottom: 24 }}>
                <div className="card-title"><ShieldCheck size={14} /> Loan Details</div>
                <div className="card-grid card-grid-3">
                    <div className="form-group">
                        <label className="form-label">Company Name *</label>
                        <input className="form-input" value={company} onChange={e => setCompany(e.target.value)}
                            placeholder="Company name" id="rec-company-input" />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Loan Amount (₹ Crores)</label>
                        <input className="form-input" type="number" value={loanAmount} onChange={e => setLoanAmount(e.target.value)}
                            placeholder="e.g. 50" id="loan-amount-input" />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Collateral Value (₹ Crores)</label>
                        <input className="form-input" type="number" value={collateral} onChange={e => setCollateral(e.target.value)}
                            placeholder="e.g. 75" id="collateral-input" />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Loan Purpose</label>
                        <input className="form-input" value={loanPurpose} onChange={e => setLoanPurpose(e.target.value)}
                            placeholder="Working capital, Capex, Acquisition…" id="loan-purpose-input" />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Tenure (Months)</label>
                        <select className="form-select" value={tenure} onChange={e => setTenure(e.target.value)} id="tenure-select">
                            {[12, 24, 36, 48, 60, 84, 120].map(m => (
                                <option key={m} value={m}>{m} months ({(m / 12).toFixed(0)}yr{m > 12 ? 's' : ''})</option>
                            ))}
                        </select>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                        <button
                            className="btn btn-primary w-full"
                            onClick={handleGenerate}
                            disabled={loading}
                            id="generate-rec-btn"
                        >
                            {loading
                                ? <><span className="spinner" /> Generating…</>
                                : <><ShieldCheck size={16} /> Generate Recommendation</>
                            }
                        </button>
                    </div>
                </div>
            </div>

            {/* Results */}
            {result && (
                <>
                    {/* Decision Banner */}
                    <div style={{ marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                        <div className={`decision-badge ${decisionClass}`} style={{ fontSize: 18, padding: '14px 24px' }}>
                            {result.decision === 'APPROVE' ? <CheckCircle size={22} /> :
                                result.decision === 'REJECT' ? <X size={22} /> :
                                    <AlertTriangle size={22} />}
                            {result.decision.replace('_', ' ')}
                        </div>
                        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                            {result.recommended_loan_amount && (
                                <div className="stat-card" style={{ padding: '12px 20px' }}>
                                    <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>RECOMMENDED AMOUNT</div>
                                    <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--accent-green)' }}>₹{result.recommended_loan_amount?.toFixed(1)} Cr</div>
                                </div>
                            )}
                            {result.recommended_interest_rate && (
                                <div className="stat-card" style={{ padding: '12px 20px' }}>
                                    <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>INTEREST RATE</div>
                                    <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--gold)' }}>{result.recommended_interest_rate}%</div>
                                </div>
                            )}
                            <div className="stat-card" style={{ padding: '12px 20px' }}>
                                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>RISK PREMIUM</div>
                                <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--accent-orange)' }}>{result.risk_premium_bps} bps</div>
                            </div>
                            <div className="stat-card" style={{ padding: '12px 20px' }}>
                                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>CREDIT GRADE</div>
                                <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--accent-cyan)' }}>{result.five_c_scores?.grade}</div>
                            </div>
                        </div>
                    </div>

                    {/* Five Cs Gauges */}
                    <div className="card" style={{ marginBottom: 20 }}>
                        <div className="card-title"><TrendingUp size={14} /> Five-Cs Score Breakdown</div>
                        <div style={{ display: 'flex', gap: 24, justifyContent: 'space-around', flexWrap: 'wrap', marginBottom: 24 }}>
                            {['character', 'capacity', 'capital', 'collateral', 'conditions'].map(c => (
                                <ScoreRing
                                    key={c}
                                    value={result.five_c_scores[c] || 0}
                                    color={FIVE_C_COLORS[c]}
                                    label={c.charAt(0).toUpperCase() + c.slice(1)}
                                />
                            ))}
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                            <div>
                                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>RADAR VIEW</div>
                                <ResponsiveContainer width="100%" height={220}>
                                    <RadarChart data={radarData}>
                                        <PolarGrid stroke="rgba(255,255,255,0.08)" />
                                        <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                                        <Radar dataKey="score" stroke="#C8A84B" fill="#C8A84B" fillOpacity={0.2} strokeWidth={2} />
                                        <Tooltip contentStyle={{ background: '#0D1B4B', border: '1px solid rgba(200,168,75,0.3)', borderRadius: 8 }} />
                                    </RadarChart>
                                </ResponsiveContainer>
                            </div>
                            <div>
                                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>BAR VIEW</div>
                                <ResponsiveContainer width="100%" height={220}>
                                    <BarChart data={barData} layout="vertical">
                                        <XAxis type="number" domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                                        <YAxis type="category" dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} width={80} />
                                        <Tooltip contentStyle={{ background: '#0D1B4B', border: '1px solid rgba(200,168,75,0.3)', borderRadius: 8 }} />
                                        <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                                            {barData.map((entry, i) => (
                                                <Cell key={i} fill={entry.color} />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>

                    {/* Decision Rationale */}
                    <div className="card" style={{ marginBottom: 20 }}>
                        <div className="card-title"><Info size={14} /> Decision Rationale (Explainable AI)</div>
                        <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                            {result.decision_rationale}
                        </p>
                    </div>

                    {/* Risks & Mitigants */}
                    <div className="card-grid card-grid-2" style={{ marginBottom: 20 }}>
                        <div className="card" style={{ borderColor: 'rgba(255,71,87,0.25)' }}>
                            <div className="card-title" style={{ color: 'var(--accent-red)' }}>
                                <AlertTriangle size={14} /> Key Risks
                            </div>
                            {result.key_risks?.map((r, i) => (
                                <div key={i} className="risk-flag high" style={{ marginBottom: 8 }}>
                                    {i + 1}. {r}
                                </div>
                            ))}
                        </div>
                        <div className="card" style={{ borderColor: 'rgba(0,229,160,0.25)' }}>
                            <div className="card-title" style={{ color: 'var(--accent-green)' }}>
                                <CheckCircle size={14} /> Mitigants / Conditions
                            </div>
                            {result.mitigants?.map((m, i) => (
                                <div key={i} className="risk-flag low" style={{ marginBottom: 8 }}>
                                    {i + 1}. {m}
                                </div>
                            ))}
                            {(!result.mitigants || result.mitigants.length === 0) && (
                                <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No additional conditions required.</div>
                            )}
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: 12 }}>
                        <button
                            className="btn btn-primary btn-lg"
                            onClick={() => navigate('/cam')}
                            id="go-to-cam-btn"
                        >
                            <ChevronRight size={16} /> View & Download CAM Report
                        </button>
                    </div>
                </>
            )}
        </div>
    )
}
