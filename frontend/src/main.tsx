import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import AuthGate from './auth/AuthGate'
import ResetPassword from './auth/ResetPassword'
import { isAuthEnabled } from './auth/supabase'
import './index.css'

// Sprint 09: the one deliberate route outside the auth gate. Emailed
// recovery/invite links must work from a fresh browser navigation, so
// /auth/reset-password renders its own page INSTEAD of the gated app
// (vercel.json's SPA rewrite makes the deep link reach index.html at
// all; this branch makes it mean something). Everything else mounts
// the normal gated app -- in-app navigation stays state-driven for
// now (the wider URL-routing question belongs to the Role-Aware UX
// sprint; see V1_1_RELEASE_READINESS.md's findings register).
// In unauthenticated builds (production LotSync: no Supabase env) the
// route falls through to the normal app -- no recovery flow exists
// there to serve.
const isResetRoute =
  isAuthEnabled && window.location.pathname.replace(/\/+$/, '') === '/auth/reset-password'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {isResetRoute ? (
      <ResetPassword />
    ) : (
      <AuthGate>
        <App />
      </AuthGate>
    )}
  </React.StrictMode>,
)
