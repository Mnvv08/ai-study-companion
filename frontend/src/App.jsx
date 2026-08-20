// src/App.jsx
// Root component — Phase 0: System Status & Health Dashboard.
// In Phase 1, this will be upgraded with React Router and real authentication pages.

import { useState, useEffect } from 'react'
import { Toaster, toast } from 'react-hot-toast'

export default function App() {
  const [healthData, setHealthData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [pingLatency, setPingLatency] = useState(null)

  const checkHealth = async () => {
    setLoading(true)
    setError(null)
    const startTime = performance.now()

    try {
      // In development, Vite proxies /api to http://backend:8000
      const res = await fetch('/api/v1/health')
      const latency = Math.round(performance.now() - startTime)
      setPingLatency(latency)

      if (!res.ok) {
        throw new Error(`HTTP Error ${res.status}: ${res.statusText}`)
      }

      const data = await res.json()
      setHealthData(data)
      toast.success('Connected to backend successfully!', { id: 'health-toast' })
    } catch (err) {
      console.error('Health check failed:', err)
      setError(err.message || 'Failed to reach backend')
      setHealthData(null)
      toast.error('Cannot connect to backend', { id: 'health-toast' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    checkHealth()
  }, [])

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-indigo-500 selection:text-white">
      <Toaster position="top-right" toastOptions={{ style: { background: '#0f172a', color: '#f8fafc', border: '1px solid #334155' } }} />

      {/* Background Decorative Gradients */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-indigo-600/15 rounded-full blur-3xl"></div>
        <div className="absolute top-1/3 -right-40 w-96 h-96 bg-violet-600/15 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 left-1/3 w-96 h-96 bg-emerald-600/10 rounded-full blur-3xl"></div>
      </div>

      {/* Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/40 backdrop-blur-md sticky top-0 z-10 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-xl shadow-lg shadow-indigo-500/25">
              🎓
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
                AI Study Companion
                <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-medium border border-indigo-500/30">
                  Phase 0
                </span>
              </h1>
              <p className="text-xs text-slate-400">Scaffolding & Architecture Verification</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-medium text-slate-300 hover:text-white px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/60 hover:bg-slate-800 transition flex items-center gap-1.5"
            >
              <span>Swagger API Docs</span>
              <span>↗</span>
            </a>
            <a
              href="http://localhost:8000/redoc"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-medium text-slate-300 hover:text-white px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/60 hover:bg-slate-800 transition flex items-center gap-1.5"
            >
              <span>ReDoc</span>
              <span>↗</span>
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-10 w-full flex-grow flex flex-col justify-center">
        {/* Hero title */}
        <div className="text-center mb-10 space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            Phase 0 Scaffolding Ready
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
            System Connectivity & Environment Status
          </h2>
          <p className="text-slate-400 max-w-xl mx-auto text-sm sm:text-base">
            Docker Compose architecture is running: FastAPI backend, PostgreSQL database, ChromaDB vector store, and React frontend.
          </p>
        </div>

        {/* Status Dashboard Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {/* Frontend Card */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-sm relative overflow-hidden group hover:border-slate-700 transition">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Frontend Service</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                ● Live (:5173)
              </span>
            </div>
            <div className="text-xl font-bold text-white mb-1">React + Vite</div>
            <p className="text-xs text-slate-400">Tailwind CSS, Zustand, React Router</p>
          </div>

          {/* Backend Card */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-sm relative overflow-hidden group hover:border-slate-700 transition">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Backend Service</span>
              {loading ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/15 text-amber-300 border border-amber-500/30">
                  Checking...
                </span>
              ) : healthData?.status === 'ok' ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  ● Healthy (:8000)
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-rose-500/15 text-rose-400 border border-rose-500/30">
                  ✕ Offline
                </span>
              )}
            </div>
            <div className="text-xl font-bold text-white mb-1">FastAPI (Python 3.11)</div>
            <p className="text-xs text-slate-400">
              {pingLatency ? `Latency: ${pingLatency}ms` : 'Pydantic Settings, Uvicorn'}
            </p>
          </div>

          {/* Database Card */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-sm relative overflow-hidden group hover:border-slate-700 transition">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Relational Database</span>
              {loading ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/15 text-amber-300 border border-amber-500/30">
                  Checking...
                </span>
              ) : healthData?.database === 'connected' ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  ● Connected (:5432)
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-rose-500/15 text-rose-400 border border-rose-500/30">
                  ✕ Unreachable
                </span>
              )}
            </div>
            <div className="text-xl font-bold text-white mb-1">PostgreSQL 15</div>
            <p className="text-xs text-slate-400">SQLAlchemy 2.0 ORM, Session Pool</p>
          </div>
        </div>

        {/* Live Health Check Raw Response Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4 pb-4 border-b border-slate-800">
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <span className="inline-block w-2 h-2 rounded-full bg-indigo-400"></span>
                Endpoint Response: <code className="text-xs bg-slate-800 text-indigo-300 px-2 py-0.5 rounded">GET /api/v1/health</code>
              </h3>
              <p className="text-xs text-slate-400 mt-1">Live probe verifying end-to-end communication via Vite proxy</p>
            </div>
            <button
              onClick={checkHealth}
              disabled={loading}
              className="self-start sm:self-auto px-4 py-2 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-xs font-medium transition shadow-lg shadow-indigo-600/20 flex items-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                  </svg>
                  <span>Probing...</span>
                </>
              ) : (
                <>
                  <span>↻</span>
                  <span>Test Connection</span>
                </>
              )}
            </button>
          </div>

          <div className="bg-slate-950 rounded-xl p-4 border border-slate-800/80 font-mono text-xs overflow-x-auto">
            {loading && !healthData && (
              <div className="text-slate-500 italic py-2">Executing query to FastAPI...</div>
            )}
            {error && (
              <div className="text-rose-400 py-1">
                ⚠️ Error: {error}
                <div className="text-slate-500 text-xs mt-2 font-sans">
                  Tip: Ensure Docker containers are running using <code>docker compose up --build</code>.
                </div>
              </div>
            )}
            {healthData && (
              <pre className="text-emerald-400">
                {JSON.stringify(healthData, null, 2)}
              </pre>
            )}
          </div>
        </div>

        {/* Phase RoadMap Overview */}
        <div className="mt-8 bg-indigo-950/20 border border-indigo-900/30 rounded-2xl p-5">
          <h4 className="text-xs font-bold text-indigo-300 uppercase tracking-wider mb-2">Next Step: Phase 1 (MVP)</h4>
          <p className="text-xs text-slate-300 leading-relaxed">
            Once Phase 0 is verified, we will build JWT User Authentication, PDF File Upload & Validation, Text Chunking, ChromaDB Vector Embeddings, RAG Q&amp;A, and Structured Notes Generation.
          </p>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/60 bg-slate-950/80 py-4 px-6 text-center text-xs text-slate-500">
        AI Study Companion • Phase 0 Scaffolding • FastAPI + PostgreSQL + ChromaDB + React
      </footer>
    </div>
  )
}
