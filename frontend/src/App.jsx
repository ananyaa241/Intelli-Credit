import { Routes, Route, Navigate } from 'react-router-dom'
import { AppProvider } from './context/AppContext'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import IngestorPage from './pages/IngestorPage'
import ResearchPage from './pages/ResearchPage'
import RecommendationPage from './pages/RecommendationPage'
import CAMPage from './pages/CAMPage'

export default function App() {
  return (
    <AppProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/ingestor" element={<IngestorPage />} />
          <Route path="/research" element={<ResearchPage />} />
          <Route path="/recommendation" element={<RecommendationPage />} />
          <Route path="/cam" element={<CAMPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </AppProvider>
  )
}
