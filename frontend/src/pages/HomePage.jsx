import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Zap, Upload, Search, ShieldCheck, FileText, ArrowRight, TrendingUp, Shield, Clock } from 'lucide-react'

const PILLARS = [
    {
        icon: Upload,
        color: '#00D4FF',
        bg: 'rgba(0,212,255,0.12)',
        title: 'Data Ingestor',
        desc: 'Parse multi-format documents — PDFs, GST returns, bank statements. Cross-verify for circular trading.',
        step: '01',
    },
    {
        icon: Search,
        color: '#C8A84B',
        bg: 'rgba(200,168,75,0.12)',
        title: 'Research Agent',
        desc: 'Web-scale secondary research on promoters, sector headwinds, litigation, and regulatory updates.',
        step: '02',
    },
    {
        icon: ShieldCheck,
        color: '#00E5A0',
        bg: 'rgba(0,229,160,0.12)',
        title: 'Recommendation Engine',
        desc: 'Transparent Five-Cs scoring with AI-powered rationale. Generate professional CAM PDF reports.',
        step: '03',
    },
]

const FEATURES = [
    { icon: TrendingUp, label: 'GSTR-2A vs 3B Cross-check' },
    { icon: Shield, label: 'Explainable AI Logic' },
    { icon: Search, label: 'eCourt & MCA Filings' },
    { icon: Clock, label: 'Minutes vs Weeks' },
    { icon: FileText, label: 'Auto CAM Generation' },
    { icon: Zap, label: 'India-Context Aware' },
]

export default function HomePage() {
    const navigate = useNavigate()
    const { sessionId } = useApp()

    return (
        <div className="hero-section">
            <div
                style={{
                    position: 'absolute', inset: 0, overflow: 'hidden',
                    background: `
            radial-gradient(ellipse at 70% 10%, rgba(200,168,75,0.08) 0%, transparent 50%),
            radial-gradient(ellipse at 20% 80%, rgba(0,212,255,0.05) 0%, transparent 50%)
          `,
                    pointerEvents: 'none',
                }}
            />

            <div className="hero-badge">
                <Zap size={12} />
                AI-Powered Credit Intelligence
            </div>

            <h1 className="hero-title">
                Next-Gen Corporate<br />
                <span className="hero-title-gradient">Credit Appraisal</span>
            </h1>

            <p className="hero-desc">
                Intelli-Credit automates end-to-end CAM preparation for Indian corporate lending —
                ingesting multi-source data, performing deep web research, and generating explainable
                credit decisions in minutes, not weeks.
            </p>

            <div className="hero-features">
                {FEATURES.map(({ icon: Icon, label }) => (
                    <div key={label} className="hero-feature-chip">
                        <Icon size={13} style={{ color: 'var(--gold)' }} />
                        {label}
                    </div>
                ))}
            </div>

            <div style={{ display: 'flex', gap: 12, marginBottom: 64 }}>
                <button
                    className="btn btn-primary btn-lg"
                    onClick={() => navigate('/ingestor')}
                >
                    <Upload size={18} />
                    Start New Appraisal
                    <ArrowRight size={16} />
                </button>
                {sessionId && (
                    <button
                        className="btn btn-secondary btn-lg"
                        onClick={() => navigate('/recommendation')}
                    >
                        Continue Session
                    </button>
                )}
            </div>

            {/* Three pillars */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20, maxWidth: 900, width: '100%' }}>
                {PILLARS.map(({ icon: Icon, color, bg, title, desc, step }) => (
                    <div
                        key={title}
                        className="card"
                        style={{ textAlign: 'left', position: 'relative', overflow: 'hidden', cursor: 'pointer' }}
                        onClick={() => navigate(
                            step === '01' ? '/ingestor' : step === '02' ? '/research' : '/recommendation'
                        )}
                    >
                        <div
                            style={{
                                position: 'absolute', top: 12, right: 12,
                                fontSize: 48, fontFamily: 'var(--font-display)',
                                fontWeight: 900, color: 'rgba(255,255,255,0.03)',
                                lineHeight: 1,
                            }}
                        >
                            {step}
                        </div>

                        <div style={{
                            width: 44, height: 44, borderRadius: 10,
                            background: bg, border: `1px solid ${color}30`,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            marginBottom: 14,
                        }}>
                            <Icon size={22} style={{ color }} />
                        </div>

                        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>{title}</div>
                        <div style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.6 }}>{desc}</div>

                        <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 6, color, fontSize: 12, fontWeight: 600 }}>
                            Go to Step <ArrowRight size={13} />
                        </div>
                    </div>
                ))}
            </div>

            <div style={{ marginTop: 40, fontSize: 11, color: 'var(--text-muted)', letterSpacing: 1 }}>
                POWERED BY GOOGLE GEMINI · SERPER SEARCH · INDIAN CREDIT STANDARDS
            </div>
        </div>
    )
}
