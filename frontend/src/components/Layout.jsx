import { NavLink, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useApp } from '../context/AppContext'
import { checkHealth } from '../api'
import {
    LayoutDashboard, Upload, Search, ShieldCheck, FileText,
    Zap, RotateCcw, Circle
} from 'lucide-react'

const NAV_ITEMS = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/ingestor', label: 'Data Ingestor', icon: Upload, badge: '1' },
    { to: '/research', label: 'Research Agent', icon: Search, badge: '2' },
    { to: '/recommendation', label: 'Recommendation', icon: ShieldCheck, badge: '3' },
    { to: '/cam', label: 'CAM Report', icon: FileText, badge: '4' },
]

export default function Layout({ children }) {
    const { sessionId, companyName, toasts, reset } = useApp()
    const [health, setHealth] = useState(null)
    const navigate = useNavigate()

    useEffect(() => {
        checkHealth()
            .then(r => setHealth(r.data))
            .catch(() => setHealth(null))
    }, [])

    const handleReset = () => {
        if (window.confirm('Start a new session? This will clear all current data.')) {
            reset()
            navigate('/')
        }
    }

    return (
        <div className="app-root">
            {/* ── Sidebar ────────────────────────────────────────────── */}
            <aside className="sidebar">
                <div className="sidebar-logo">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div style={{
                            width: 36, height: 36,
                            background: 'linear-gradient(135deg, #C8A84B, #E8C86A)',
                            borderRadius: 8,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}>
                            <Zap size={18} color="#0D1B4B" strokeWidth={2.5} />
                        </div>
                        <div>
                            <div className="sidebar-logo-text">Intelli-Credit</div>
                            <div className="sidebar-logo-sub">AI Credit Engine</div>
                        </div>
                    </div>

                    {companyName && (
                        <div style={{
                            marginTop: 12,
                            padding: '8px 10px',
                            background: 'rgba(200,168,75,0.08)',
                            border: '1px solid rgba(200,168,75,0.2)',
                            borderRadius: 8,
                            fontSize: 12,
                            color: '#C8A84B',
                        }}>
                            <div style={{ fontSize: 10, opacity: 0.7, marginBottom: 2 }}>ACTIVE SESSION</div>
                            <div style={{ fontWeight: 600 }}>{companyName}</div>
                            {sessionId && (
                                <div style={{ fontSize: 10, opacity: 0.5, marginTop: 2, fontFamily: 'monospace' }}>
                                    {sessionId.slice(0, 16)}…
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <nav className="sidebar-nav">
                    <div className="nav-section-label">Navigation</div>

                    {NAV_ITEMS.map(({ to, label, icon: Icon, badge }) => (
                        <NavLink
                            key={to}
                            to={to}
                            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
                        >
                            <Icon size={17} className="nav-item-icon" />
                            <span>{label}</span>
                            {badge && <span className="nav-badge">{badge}</span>}
                        </NavLink>
                    ))}

                    <div className="section-divider" style={{ marginTop: 8 }} />

                    {sessionId && (
                        <>
                            <div className="nav-section-label">Session</div>
                            <button className="nav-item btn-danger" style={{ width: '100%', border: 'none', background: 'transparent', color: '#FF6B7A', cursor: 'pointer' }} onClick={handleReset}>
                                <RotateCcw size={17} />
                                <span>New Session</span>
                            </button>
                        </>
                    )}
                </nav>

                <div className="sidebar-status">
                    {health ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span className={`status-dot ${health.gemini_configured ? 'online' : 'offline'}`} />
                            <div>
                                <div style={{ fontSize: 11, color: health.gemini_configured ? '#00E5A0' : '#FF4757', fontWeight: 600 }}>
                                    {health.gemini_configured ? 'AI Online' : 'AI Offline'}
                                </div>
                                <div className="status-text">
                                    Serper: {health.serper_configured ? '✓' : '✗'}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span className="status-dot offline" />
                            <span className="status-text">Backend offline</span>
                        </div>
                    )}
                </div>
            </aside>

            {/* ── Main ──────────────────────────────────────────────── */}
            <main className="main-content">
                {children}
            </main>

            {/* ── Toasts ────────────────────────────────────────────── */}
            <div className="toast-container">
                {toasts.map(t => (
                    <div key={t.id} className={`toast ${t.type}`}>
                        <span>{t.type === 'success' ? '✓' : t.type === 'error' ? '✕' : 'ℹ'}</span>
                        {t.message}
                    </div>
                ))}
            </div>
        </div>
    )
}
