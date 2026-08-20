// src/App.jsx
// Root component — Phase 0 skeleton only.
// In Phase 1, this will set up React Router with protected routes.

import { Toaster } from 'react-hot-toast'

export default function App() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-950">
      {/* Global toast notifications — will be used throughout the app */}
      <Toaster position="top-right" toastOptions={{ style: { background: '#1f2937', color: '#fff' } }} />

      {/* Phase 0 placeholder — replaced in Phase 1 with Router + Pages */}
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold text-white">
          🎓 AI Study Companion
        </h1>
        <p className="text-gray-400 text-lg">
          Phase 0 — Scaffold complete. Backend + DB should be running.
        </p>
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block mt-4 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors font-medium"
        >
          Open API Docs →
        </a>
      </div>
    </div>
  )
}
