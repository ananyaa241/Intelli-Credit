import { createContext, useContext, useState, useCallback, useEffect } from 'react'

const AppContext = createContext(null)

const LS_KEY = 'intellicredit_session'

function loadFromStorage() {
    try {
        const raw = localStorage.getItem(LS_KEY)
        if (!raw) return {}
        return JSON.parse(raw)
    } catch {
        return {}
    }
}

function saveToStorage(obj) {
    try {
        localStorage.setItem(LS_KEY, JSON.stringify(obj))
    } catch {
        // localStorage might be unavailable in some environments
    }
}

export function AppProvider({ children }) {
    const saved = loadFromStorage()

    const [sessionId, _setSessionId] = useState(saved.sessionId || null)
    const [companyName, _setCompanyName] = useState(saved.companyName || '')
    const [extractedData, _setExtractedData] = useState(saved.extractedData || null)
    const [researchData, _setResearchData] = useState(saved.researchData || null)
    const [recommendation, _setRecommendation] = useState(saved.recommendation || null)
    const [toasts, setToasts] = useState([])

    // Wrapped setters that also sync to localStorage
    const setSessionId = useCallback((val) => {
        _setSessionId(val)
        saveToStorage({ ...loadFromStorage(), sessionId: val })
    }, [])

    const setCompanyName = useCallback((val) => {
        _setCompanyName(val)
        saveToStorage({ ...loadFromStorage(), companyName: val })
    }, [])

    const setExtractedData = useCallback((val) => {
        _setExtractedData(val)
        saveToStorage({ ...loadFromStorage(), extractedData: val })
    }, [])

    const setResearchData = useCallback((val) => {
        _setResearchData(val)
        saveToStorage({ ...loadFromStorage(), researchData: val })
    }, [])

    const setRecommendation = useCallback((val) => {
        _setRecommendation(val)
        saveToStorage({ ...loadFromStorage(), recommendation: val })
    }, [])

    const addToast = useCallback((message, type = 'info') => {
        const id = Date.now()
        setToasts(prev => [...prev, { id, message, type }])
        setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 5000)
    }, [])

    const reset = useCallback(() => {
        _setSessionId(null)
        _setCompanyName('')
        _setExtractedData(null)
        _setResearchData(null)
        _setRecommendation(null)
        localStorage.removeItem(LS_KEY)
    }, [])

    return (
        <AppContext.Provider value={{
            sessionId, setSessionId,
            companyName, setCompanyName,
            extractedData, setExtractedData,
            researchData, setResearchData,
            recommendation, setRecommendation,
            toasts, addToast,
            reset,
        }}>
            {children}
        </AppContext.Provider>
    )
}

export const useApp = () => {
    const ctx = useContext(AppContext)
    if (!ctx) throw new Error('useApp must be inside AppProvider')
    return ctx
}
