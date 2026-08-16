import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import AuthGate from './auth/AuthGate'
import './index.css'

// Sprint 05: the operational app mounts only through the auth gate.
// In builds without Supabase env (production LotSync) the gate is a
// pass-through and nothing changes -- see auth/AuthGate.tsx.
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthGate>
      <App />
    </AuthGate>
  </React.StrictMode>,
)
