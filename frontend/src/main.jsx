// src/main.jsx
// Entry point — mounts the React app into the #root div in index.html

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  // StrictMode: Runs components twice in dev to detect side effects.
  // Has zero effect in production. Good habit to keep.
  <StrictMode>
    <App />
  </StrictMode>,
)
