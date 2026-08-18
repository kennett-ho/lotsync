/**
 * Sprint 09 -- the authenticated identity context (Phase 15/17/18).
 *
 * One /me fetch per session, shared through React context, replacing
 * scattered per-component fetches. Three jobs:
 *
 * 1. Provide the server-derived identity (email, display name, role,
 *    dealership) to every consumer -- IdentityFooter, Profile,
 *    Settings, User Management. Nothing here is client-decided.
 * 2. Distinguish the two failure classes (Phase 18):
 *      401 (from any API call, via AUTH_EXPIRED_EVENT) -> the session
 *      is genuinely dead beyond silent refresh -> clean sign-out back
 *      to the login screen.
 *      403 on /me -> authenticated but NOT authorized for this
 *      dealership (deactivated membership / offboarded / wrong store)
 *      -> the dedicated Access Denied screen with sign-out. Per-action
 *      403s elsewhere stay page-level and never reach this screen.
 * 3. Expose refresh() so Settings can re-read identity after a
 *    display-name change.
 *
 * A deactivated user's flow: their next API call 403s (server re-reads
 * membership per request), screens show errors; when /me itself is
 * re-fetched (mount/refresh) the account-level denial renders the
 * dedicated screen -- no loops, no crash, no detail leakage.
 */

import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { ApiError, apiGet, AUTH_EXPIRED_EVENT } from '../api/client'
import { identifyAnalyticsUser } from '../observability/analytics'
import { signOut } from './AuthGate'

export interface Me {
  authenticated: boolean
  auth_mode: string
  // Sprint 11: the stable internal Supabase user UUID -- the analytics
  // identity (non-PII; email/display name are never sent to telemetry).
  auth_user_id?: string
  email?: string | null
  display_name?: string | null
  role?: string
  organization?: { id: string; name: string }
  dealership?: { id: string; name: string }
}

type AccessState =
  | { status: 'loading' }
  | { status: 'ready'; me: Me }
  | { status: 'denied' }        // 403 on /me -- no active membership
  | { status: 'error'; message: string }

const AccessContext = createContext<{
  state: AccessState
  refresh: () => void
}>({ state: { status: 'loading' }, refresh: () => {} })

export function useAccess() {
  return useContext(AccessContext)
}

/** The current identity, or null while loading/denied. */
export function useMe(): Me | null {
  const { state } = useAccess()
  return state.status === 'ready' ? state.me : null
}

export const ROLE_LABELS: Record<string, string> = {
  admin: 'Admin',
  manager: 'Manager',
  lot_staff: 'Lot Staff',
  sales_manager: 'Sales Manager',
}

function AccessDenied() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4"
         style={{ backgroundColor: '#0B1220' }}>
      <div className="w-full max-w-sm rounded-xl p-6 border border-white/10 text-center"
           style={{ backgroundColor: '#111B2E' }}>
        <div className="text-white text-[15px] font-semibold mb-2">
          Account access is disabled
        </div>
        <p className="text-white/50 text-[12px] mb-5">
          Your account doesn&rsquo;t currently have access to this dealership.
          If you believe this is a mistake, contact your manager or
          administrator.
        </p>
        <button
          onClick={() => { void signOut() }}
          className="w-full rounded-md py-2.5 text-[13px] font-semibold text-white"
          style={{ backgroundColor: '#1D4ED8' }}>
          Sign Out
        </button>
      </div>
    </div>
  )
}

export default function AccessProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AccessState>({ status: 'loading' })

  const load = useCallback(() => {
    setState({ status: 'loading' })
    apiGet<Me>('/me')
      .then(me => {
        // Sprint 11: identify analytics AFTER the server confirms the
        // membership -- internal UUID + safe ids only, no-op when
        // PostHog is unconfigured. signOut() resets it.
        if (me.authenticated && me.auth_user_id) {
          identifyAnalyticsUser(me.auth_user_id, {
            role: me.role,
            dealership_id: me.dealership?.id,
            organization_id: me.organization?.id,
          })
        }
        setState({ status: 'ready', me })
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 403) {
          setState({ status: 'denied' })
        } else if (error instanceof ApiError && error.status === 401) {
          // AUTH_EXPIRED_EVENT listener below handles the sign-out;
          // keep a quiet loading state meanwhile.
          setState({ status: 'loading' })
        } else {
          setState({
            status: 'error',
            message: 'Could not load your account right now.',
          })
        }
      })
  }, [])

  useEffect(() => { load() }, [load])

  // Phase 18: a 401 anywhere means the session is dead beyond
  // supabase-js's silent refresh -- return to login cleanly.
  useEffect(() => {
    const onExpired = () => { void signOut() }
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired)
  }, [])

  if (state.status === 'denied') return <AccessDenied />

  return (
    <AccessContext.Provider value={{ state, refresh: load }}>
      {children}
    </AccessContext.Provider>
  )
}
