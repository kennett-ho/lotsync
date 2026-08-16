/**
 * Sprint 05 -- the signed-in identity block in the sidebar footer:
 * who you are, your role, your dealership, Sign Out. Sprint 09: reads
 * the shared AccessProvider context (one /me per session) instead of
 * fetching itself, and leads with the display name when the person
 * has set one in Settings.
 */

import { ROLE_LABELS, useMe } from './AccessProvider'
import { signOut } from './AuthGate'

export default function IdentityFooter() {
  const me = useMe()

  const primary = me?.display_name || me?.email || '…'
  const secondaryEmail = me?.display_name ? me?.email ?? '' : ''
  const role = me?.role ? (ROLE_LABELS[me.role] ?? me.role) : ''
  const dealership = me?.dealership?.name ?? ''

  return (
    <div className="px-3 pb-3 pt-2 border-t border-white/10">
      <div className="px-2.5 py-2">
        <div className="text-white text-[12px] font-semibold truncate" title={primary}>
          {primary}
        </div>
        {secondaryEmail && (
          <div className="text-white/40 text-[11px] truncate" title={secondaryEmail}>
            {secondaryEmail}
          </div>
        )}
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
