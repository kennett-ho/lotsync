/**
 * Sprint 05 -- the signed-in identity block in the sidebar footer
 * (spec Phase 15): who you are, your role, your dealership, Sign Out.
 * Everything displayed comes from GET /me -- the server-derived
 * membership truth -- never from anything client-side, and there is
 * deliberately no way to switch roles here: testing another role
 * means signing in as another synthetic account.
 */

import { useApi } from '../api/useApi'
import { apiGet } from '../api/client'
import { signOut } from './AuthGate'

interface MeResponse {
  authenticated: boolean
  auth_mode: string
  email?: string | null
  role?: string
  organization?: { id: string; name: string }
  dealership?: { id: string; name: string }
}

const ROLE_LABELS: Record<string, string> = {
  admin: 'Admin',
  manager: 'Manager',
  lot_staff: 'Lot Staff',
  sales_manager: 'Sales Manager',
}

export default function IdentityFooter() {
  const me = useApi(() => apiGet<MeResponse>('/me'), [])

  const email = me.data?.email ?? '…'
  const role = me.data?.role ? (ROLE_LABELS[me.data.role] ?? me.data.role) : ''
  const dealership = me.data?.dealership?.name ?? ''

  return (
    <div className="px-3 pb-3 pt-2 border-t border-white/10">
      <div className="px-2.5 py-2">
        <div className="text-white text-[12px] font-semibold truncate" title={email}>
          {email}
        </div>
        <div className="text-white/50 text-[11px] truncate">
          {role}{role && dealership ? ' · ' : ''}{dealership}
        </div>
      </div>
      <button
        onClick={() => { void signOut() }}
        className="w-full flex items-center justify-center gap-2 px-2.5 py-2 rounded-md text-[12px] font-semibold text-white/80 border border-white/10 transition-colors hover:bg-white/5"
      >
        <svg width="13" height="13" fill="none" viewBox="0 0 24 24">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"
                stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Sign Out
      </button>
    </div>
  )
}
