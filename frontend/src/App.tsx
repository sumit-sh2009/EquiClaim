import { Route, Routes } from 'react-router-dom'
import { ClaimDetailPage } from './pages/ClaimDetailPage'
import { LedgerPage } from './pages/LedgerPage'
import { UploadPage } from './pages/UploadPage'

function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-4xl px-4 py-3">
          <span className="text-lg font-bold tracking-tight text-slate-900">EquiClaim</span>
          <span className="ml-2 text-xs text-slate-400">forensic audit engine</span>
        </div>
      </header>
      <Routes>
        <Route path="/" element={<LedgerPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/claims/:claimId" element={<ClaimDetailPage />} />
      </Routes>
    </div>
  )
}

export default App
