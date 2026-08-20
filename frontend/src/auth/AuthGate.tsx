/**
 * Sprint 05 -- the authentication gate around the operational app.
 *
 *   auth disabled (production build)  -> children, untouched
 *   enabled + no session              -> Login (the app never mounts)
 *   enabled + session                 -> children
 *
 * Session state comes from supabase-js (persisted in localStorage,
 * auto-refreshed), subscribed via onAuthStateChange so sign-in,
 * sign-out, refresh, and token renewal all flow through one place.
 * This gate is UX flow only -- the SECURITY boundary is the FastAPI
 * layer, which independently verifies every request's token and
 * membership (see api/auth.py); nothing here is trusted server-side.
 */

import { Suspense, lazy, useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { resetAnalyticsIdentity } from '../observability/analytics'
import AccessProvider from './AccessProvider'
import { isAuthEnabled, supabase } from './supabase'

// Sprint 14 (Rail J): the login screen is its own chunk -- production
// builds (auth disabled) never render it, and authenticated sessions
// skip it too.
const Login = lazy(() => import('./Login'))

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [ready, setReady] = useState(!isAuthEnabled)

  useEffect(() => {
    if (!supabase) return
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setReady(true)
    })
    const { data: subscription } = supabase.auth.onAuthStateChange(
      (_event, nextSession) => setSession(nextSession),
    )
    return () => subscription.subscription.unsubscribe()
  }, [])

  if (!isAuthEnabled) return <>{children}</>

  if (!ready) {
    // Brief splash while the persisted session is read back -- avoids
    // flashing the login screen at an already-signed-in user on
    // refresh.
    return (
      <div className="min-h-screen flex items-center justify-center"
           style={{ backgroundColor: '#0B1220' }}>
        <div className="text-white/40 text-[13px]">Loading DealerDOH…</div>
      </div>
    )
  }

  if (!session) {
    return (
      <Suspense fallback={
        <div className="min-h-screen" style={{ backgroundColor: '#0B1220' }} />
      }>
        <Login />
      </Suspense>
    )
  }

  // Sprint 09: the signed-in app runs inside AccessProvider -- one
  // shared /me identity, account-level denial handling (disabled
  // membership -> dedicated screen), and global 401 -> clean sign-out.
  return <AccessProvider>{children}</AccessProvider>
}

export async function signOut(): Promise<void> {
  // Sprint 11: every sign-out path funnels through here (user click,
  // 401 expiry, post-reset global sign-out), so this is THE place
  // analytics identity is severed -- User B on this browser never
  // inherits User A's identity. Reset happens even if the Supabase
  // call fails.
  resetAnalyticsIdentity()
  if (supabase) await supabase.auth.signOut()
  // onAuthStateChange above flips the gate back to Login; no manual
  // navigation or reload needed.
}
