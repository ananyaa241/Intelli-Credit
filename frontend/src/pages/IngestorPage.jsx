import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, X, FileText, AlertTriangle, CheckCircle, ChevronRight, Info, Edit2, Key, List as ListIcon, Database } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { uploadDocuments, extractData } from '../api'

const DEFAULT_SCHEMA = {
  "revenue_cr": "number or null",
  "ebitda_cr": "number or null",
  "pat_cr": "number or null",
  "total_debt_cr": "number or null",
  "net_worth_cr": "number or null",
  "current_ratio": "number or null",
  "debt_equity_ratio": "number or null",
  "interest_coverage_ratio": "number or null",
  "dscr": "number or null",
  "roce_pct": "number or null",
  "roe_pct": "number or null"
}

const CATEGORIES = [
  "Financial Statement",
  "Bank Statement",
  "Legal Notice",
  "Rating Report",
  "GST Return",
  "Other"
]

const GST_PLACEHOLDER = JSON.stringify({
    monthly_turnover: { "2024-01": 5000000, "2024-02": 5200000 },
    gstr_3b_tax_paid: { "2024-01": 900000, "2024-02": 936000 },
    gstr_2a_itc_claimed: { "2024-01": 750000, "2024-02": 780000 },
}, null, 2)

const BANK_PLACEHOLDER = JSON.stringify({
    monthly_credits: { "2024-01": 5100000, "2024-02": 5400000 },
}, null, 2)

export default function IngestorPage() {
    const navigate = useNavigate()
    const { setSessionId, setCompanyName: setGlobalName, setExtractedData, addToast } = useApp()

    // Step state
    const [step, setStep] = useState(1) // 1: Upload, 2: Classify, 3: Schema, 4: Verify
    const [loading, setLoading] = useState(false)

    // Step 1: Upload state
    const [companyName, setCompanyName] = useState('')
    const [files, setFiles] = useState([])
    const [dragOver, setDragOver] = useState(false)
    const fileRef = useRef()

    // Step 2: Classify state
    const [sessionIdLocal, setSessionIdLocal] = useState('')
    const [documents, setDocuments] = useState([]) // [{ filename, category, raw_text_length }]

    // Step 3: Schema state
    const [schemaStr, setSchemaStr] = useState(JSON.stringify(DEFAULT_SCHEMA, null, 2))
    const [gstJson, setGstJson] = useState('')
    const [bankJson, setBankJson] = useState('')
    
    // Step 4: Verify state
    const [finalData, setFinalData] = useState(null)
    const [editableFinancials, setEditableFinancials] = useState({})

    // Upload Handlers
    const addFiles = useCallback((newFiles) => {
        const pdfs = Array.from(newFiles).filter(f => f.name.endsWith('.pdf'))
        if (pdfs.length < newFiles.length) addToast('Only PDF files are supported for parsing.', 'info')
        setFiles(prev => [...prev, ...pdfs])
    }, [addToast])

    const removeFile = (i) => setFiles(prev => prev.filter((_, idx) => idx !== i))
    
    const handleDrop = (e) => {
        e.preventDefault(); setDragOver(false)
        addFiles(e.dataTransfer.files)
    }

    const handleUpload = async () => {
        if (!companyName.trim()) return addToast('Please enter a company name.', 'error')
        if (files.length === 0) return addToast('Upload at least one PDF document.', 'error')

        setLoading(true)
        try {
            const fd = new FormData()
            files.forEach(f => fd.append('files', f))
            const { data } = await uploadDocuments(fd)
            
            setSessionIdLocal(data.session_id)
            setDocuments(data.documents)
            
            if (data.auto_gst_data && Object.keys(data.auto_gst_data.monthly_turnover || {}).length > 0) {
                setGstJson(JSON.stringify(data.auto_gst_data, null, 2))
            }
            
            setStep(2)
            addToast('Documents uploaded successfully! Please review classifications.', 'success')
        } catch (err) {
            addToast(err?.response?.data?.detail || 'Upload failed.', 'error')
        } finally {
            setLoading(false)
        }
    }

    const handleConfirmClassification = () => {
        setStep(3)
    }

    const handleExtract = async () => {
        try {
            JSON.parse(schemaStr)
        } catch (e) {
            return addToast('Invalid Schema JSON format.', 'error')
        }

        setLoading(true)
        try {
            const catDict = {}
            documents.forEach(d => { catDict[d.filename] = d.category })

            const payload = {
                company_name: companyName,
                categories: catDict,
                extraction_schema: JSON.parse(schemaStr),
                gst_json: gstJson || null,
                bank_statement_json: bankJson || null
            }
            
            const { data } = await extractData(sessionIdLocal, payload)
            
            setFinalData(data)
            setEditableFinancials(data.extracted_data?.financials || {})
            
            setStep(4)
            addToast('Data extraction complete! Please verify values.', 'success')
        } catch (err) {
            addToast(err?.response?.data?.detail || 'Extraction failed.', 'error')
        } finally {
            setLoading(false)
        }
    }

    const handleFinalise = () => {
        // Create final data object with user modifications
        const finalizedData = {
            ...finalData.extracted_data,
            financials: editableFinancials
        }
        
        setSessionId(sessionIdLocal)
        setGlobalName(companyName)
        setExtractedData(finalizedData)
        
        navigate('/research')
    }

    const renderStepIndicator = () => {
        const steps = ['Upload', 'Classify', 'Schema', 'Verify']
        return (
            <div style={{ display: 'flex', gap: 12, marginBottom: 24, alignItems: 'center' }}>
                {steps.map((s, i) => {
                    const isActive = step === i + 1
                    const isDone = step > i + 1
                    return (
                        <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 8, opacity: isActive || isDone ? 1 : 0.4 }}>
                            <div style={{
                                width: 24, height: 24, borderRadius: '50%', 
                                background: isActive ? 'var(--gold)' : (isDone ? 'var(--accent-green)' : 'var(--bg-glass)'),
                                color: isActive ? '#000' : '#fff',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                fontSize: 12, fontWeight: 'bold'
                            }}>
                                {isDone ? <CheckCircle size={14} /> : i + 1}
                            </div>
                            <span style={{ fontSize: 13, fontWeight: isActive ? 600 : 400, color: isActive ? 'var(--gold)' : 'var(--text-primary)' }}>{s}</span>
                            {i < steps.length - 1 && <div style={{ width: 30, height: 1, background: 'var(--border-glass)' }} />}
                        </div>
                    )
                })}
            </div>
        )
    }

    return (
        <div className="page">
            <div className="page-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                    <span className="tag tag-cyan">Ingestion Flow</span>
                </div>
                <h1 className="page-title">Automated Extraction & Schema Mapping</h1>
                <p className="page-subtitle">
                    Upload documents, verify document types, define extraction schema, and review the structured output.
                </p>
            </div>

            {renderStepIndicator()}

            {/* ── STEP 1: UPLOAD ──────────────────────────────────────────── */}
            {step === 1 && (
                <div className="card-grid card-grid-2">
                    <div>
                        <div className="form-group">
                            <label className="form-label">Company Name *</label>
                            <input
                                className="form-input"
                                placeholder="e.g. Reliance Industries Ltd"
                                value={companyName}
                                onChange={e => setCompanyName(e.target.value)}
                            />
                        </div>

                        <div
                            className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
                            onClick={() => fileRef.current.click()}
                            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
                            onDragLeave={() => setDragOver(false)}
                            onDrop={handleDrop}
                        >
                            <input
                                type="file"
                                ref={fileRef}
                                multiple
                                accept=".pdf"
                                style={{ display: 'none' }}
                                onChange={e => addFiles(e.target.files)}
                            />
                            <Upload size={40} style={{ color: 'var(--gold)', margin: '0 auto 12px', display: 'block' }} />
                            <div className="upload-zone-title">Drop PDFs here or click to browse</div>
                            <div className="upload-zone-sub">Upload Financials, Ratings, Legal Notices, etc.</div>
                        </div>

                        {files.length > 0 && (
                            <div style={{ marginTop: 12 }}>
                                {files.map((f, i) => (
                                    <div key={i} className="file-chip">
                                        <FileText size={12} />
                                        {f.name}
                                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>({(f.size / 1024 / 1024).toFixed(1)}MB)</span>
                                        <button className="file-chip-remove" onClick={() => removeFile(i)}>×</button>
                                    </div>
                                ))}
                            </div>
                        )}

                        <button
                            className="btn btn-primary btn-lg w-full"
                            style={{ marginTop: 20 }}
                            onClick={handleUpload}
                            disabled={loading}
                        >
                            {loading ? <><span className="spinner" /> Analyzing…</> : <><Upload size={16} /> Upload & Classify</>}
                        </button>
                    </div>

                    <div className="card" style={{ background: 'rgba(0,212,255,0.04)', borderColor: 'rgba(0,212,255,0.15)' }}>
                        <div className="card-title" style={{ color: 'var(--accent-cyan)' }}>
                            <Info size={14} /> What to Upload
                        </div>
                        {[
                            { label: 'Annual Reports', desc: 'Extract revenue, EBITDA, PAT, net worth, D/E ratio' },
                            { label: 'Financial Statements', desc: 'Balance sheet, P&L, cash flow analysis' },
                            { label: 'Rating Agency Reports', desc: 'CRISIL, ICRA, CARE – existing ratings & outlook' },
                            { label: 'Legal Notices / Sanctioned Letters', desc: 'Existing facility details, covenants' },
                        ].map(({ label, desc }) => (
                            <div key={label} style={{ marginBottom: 12 }}>
                                <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text-primary)' }}>{label}</div>
                                <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 2 }}>{desc}</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ── STEP 2: CLASSIFICATION REVIEW ───────────────────────────── */}
            {step === 2 && (
                <div className="card">
                    <div className="card-title"><ListIcon size={16}/> Review Document Classifications</div>
                    <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
                        The AI has attempted to categorize your uploaded files. If any are incorrect, please adjust them below so the extraction schema is applied properly.
                    </p>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        {documents.map((doc, index) => (
                            <div key={index} style={{ 
                                display: 'flex', alignItems: 'center', justifyContent: 'space-between', 
                                background: 'var(--bg-glass)', padding: '12px 16px', borderRadius: 'var(--radius-md)',
                                border: '1px solid var(--border-glass)'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                    <FileText size={18} style={{ color: 'var(--accent-cyan)' }}/>
                                    <span style={{ fontWeight: 500, fontSize: 14 }}>{doc.filename}</span>
                                </div>
                                <select 
                                    className="form-input" 
                                    style={{ width: '250px', margin: 0 }}
                                    value={doc.category}
                                    onChange={(e) => {
                                        const newDocs = [...documents]
                                        newDocs[index].category = e.target.value
                                        setDocuments(newDocs)
                                    }}
                                >
                                    {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                                </select>
                            </div>
                        ))}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 24 }}>
                        <button className="btn btn-primary" onClick={handleConfirmClassification}>
                            Confirm Classifications <ChevronRight size={16}/>
                        </button>
                    </div>
                </div>
            )}

            {/* ── STEP 3: SCHEMA DEFINITION ───────────────────────────────── */}
            {step === 3 && (
                <div className="card-grid card-grid-2">
                    <div className="card">
                        <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span><Database size={16}/> Definition of Extraction Schema</span>
                            <button 
                                style={{ background: 'none', border: 'none', color: 'var(--accent-cyan)', fontSize: 12, cursor: 'pointer' }}
                                onClick={() => setSchemaStr(JSON.stringify(DEFAULT_SCHEMA, null, 2))}
                            >
                                Reset to Default
                            </button>
                        </div>
                        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
                            Define the JSON structure for data you want Gemini to extract from the documents. You can add or remove keys as needed.
                        </p>
                        <textarea
                            className="form-textarea"
                            style={{ height: 320, fontFamily: 'monospace', fontSize: 13, background: '#0a0a0a' }}
                            value={schemaStr}
                            onChange={(e) => setSchemaStr(e.target.value)}
                        />
                        <button 
                            className="btn btn-primary btn-lg w-full" 
                            style={{ marginTop: 20 }}
                            onClick={handleExtract}
                            disabled={loading}
                        >
                            {loading ? <><span className="spinner"/> Extracting Data…</> : <><Key size={16}/> Run AI Extraction</>}
                        </button>
                    </div>

                    <div className="card">
                        <div className="card-title"><AlertTriangle size={16}/> Circular Trading Analysis Data</div>
                        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
                            To perform GST vs Bank Statement cross-checks for circular trading, provide the JSON equivalents manually if they were not automatically detected.
                        </p>
                        <div className="form-group">
                            <label className="form-label" style={{ fontSize: 12 }}>GSTR-3B Auto-Detection / Overrides</label>
                            <textarea
                                className="form-textarea"
                                style={{ height: 120, fontFamily: 'monospace', fontSize: 12 }}
                                placeholder={GST_PLACEHOLDER}
                                value={gstJson}
                                onChange={(e) => setGstJson(e.target.value)}
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label" style={{ fontSize: 12 }}>Bank Statement Matches</label>
                            <textarea
                                className="form-textarea"
                                style={{ height: 120, fontFamily: 'monospace', fontSize: 12 }}
                                placeholder={BANK_PLACEHOLDER}
                                value={bankJson}
                                onChange={(e) => setBankJson(e.target.value)}
                            />
                        </div>
                    </div>
                </div>
            )}

            {/* ── STEP 4: VERIFICATION ────────────────────────────────────── */}
            {step === 4 && finalData && (
                <div>
                    <div className="card" style={{ marginBottom: 24 }}>
                        <div className="card-title"><Edit2 size={16}/> Review & Adjust Extracted Values</div>
                        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
                            Review the data extracted against your definition schema. You can manually adjust the numbers before finalizing to correct any AI parsing errors.
                        </p>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
                            {Object.entries(editableFinancials).map(([key, val]) => (
                                <div key={key}>
                                    <label className="form-label" style={{ fontSize: 11, textTransform: 'uppercase', marginBottom: 4 }}>
                                        {key.replace(/_/g, ' ')}
                                    </label>
                                    <input 
                                        className="form-input" 
                                        style={{ fontFamily: 'monospace' }}
                                        value={val === null ? '' : val}
                                        onChange={(e) => {
                                            setEditableFinancials(prev => ({
                                                ...prev,
                                                [key]: e.target.value === '' ? null : e.target.value
                                            }))
                                        }}
                                    />
                                </div>
                            ))}
                            {Object.keys(editableFinancials).length === 0 && (
                                <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No fields extracted based on the schema.</div>
                            )}
                        </div>
                    </div>

                    <div className="card-grid card-grid-3" style={{ marginBottom: 24 }}>
                         <div className="stat-card">
                            <div className="stat-card-icon" style={{ background: 'rgba(0,212,255,0.12)' }}>
                                <FileText size={18} style={{ color: 'var(--accent-cyan)' }} />
                            </div>
                            <div className="stat-card-value">{documents.length}</div>
                            <div className="stat-card-label">Files Processed</div>
                        </div>
                         <div className="stat-card">
                            <div className="stat-card-icon" style={{ background: 'rgba(255,140,66,0.12)' }}>
                                <Info size={18} style={{ color: 'var(--accent-orange)' }} />
                            </div>
                            <div className="stat-card-value">{finalData.warnings?.length || 0}</div>
                            <div className="stat-card-label">Parsing Warnings</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-card-icon" style={{ background: 'rgba(255,71,87,0.12)' }}>
                                <AlertTriangle size={18} style={{ color: 'var(--accent-red)' }} />
                            </div>
                            <div className="stat-card-value">{finalData.circular_trading_flags?.length || 0}</div>
                            <div className="stat-card-label">Circular Trading Flags</div>
                        </div>
                    </div>

                     {/* Warnings */}
                     {finalData.warnings?.length > 0 && (
                        <div className="card" style={{ borderColor: 'rgba(255,140,66,0.3)', marginBottom: 24 }}>
                            <div className="card-title" style={{ color: 'var(--accent-orange)' }}>
                                <AlertTriangle size={14} /> Warnings
                            </div>
                            {finalData.warnings.map((w, i) => (
                                <div key={i} className="risk-flag medium">{w}</div>
                            ))}
                        </div>
                    )}

                    {/* Circular trading flags */}
                    {finalData.circular_trading_flags?.length > 0 && (
                        <div className="card" style={{ marginBottom: 24, borderColor: 'rgba(255,71,87,0.3)' }}>
                            <div className="card-title" style={{ color: 'var(--accent-red)' }}>
                                <AlertTriangle size={14} /> Circular Trading / Revenue Inflation Flags
                            </div>
                            {finalData.circular_trading_flags.map((f, i) => (
                                <div key={i} className="risk-flag high">⚠ {f}</div>
                            ))}
                        </div>
                    )}

                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <button className="btn btn-primary btn-lg" onClick={handleFinalise}>
                            Finalise & Proceed to Research <ChevronRight size={16}/>
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
