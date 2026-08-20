import React, { Suspense, lazy } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import AuthGate from './auth/AuthGate'
import { isAuthEnabled } from './auth/supabase'
import ErrorBoundary from './observability/ErrorBoundary'
import { initAnalytics, track } from './observability/analytics'
import { initSentry } from './observability/sentry'
import './index.css'

// Sprint 14 (Rail J): the recovery page is its own chunk -- it serves
// exactly one deep-linked route and never loads for normal app use.
const ResetPassword = lazy(() => import('./auth/ResetPassword'))

// Sprint 11 (Rails F+G): both initialize BEFORE first render and both
// are silent no-ops without their build-time config (VITE_SENTRY_DSN /
// VITE_POSTHOG_KEY) -- unconfigured builds, including the current
// production LotSync build, behave exactly as before this sprint.
initSentry()
initAnalytics()
track('app_loaded')

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
    {/* Sprint 11: the boundary sits OUTSIDE the auth gate so login/
        gate render failures get the honest fallback too. */}
    <ErrorBoundary>
      {isResetRoute ? (
        <Suspense fallback={
          <div className="min-h-screen" style={{ backgroundColor: '#0B1220' }} />
        }>
          <ResetPassword />
        </Suspense>
      ) : (
        <AuthGate>
          <App />
        </AuthGate>
      )}
    </ErrorBoundary>
  </React.StrictMode>,
)
