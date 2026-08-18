/**
 * Sprint 09 -- the honest Profile & Settings page (Rail A).
 *
 * The previous version of this page was entirely decorative: every
 * input saved to local component state, every toggle flipped nothing,
 * the session card showed a hardcoded MacBook, and Sign Out had no
 * handler. Per the ratified settings philosophy -- "if a setting
 * appears, it must work, be intentionally read-only, or be removed" --
 * this rewrite keeps ONLY what is real (the full disposition table
 * lives in ACCOUNT_LIFECYCLE.md):
 *
 *   Account   display name  -> WORKS (Supabase user_metadata, self-set)
 *             email         -> read-only (identity, Auth-owned)
 *   Access    role / dealership / organization -> read-only (server
 *             membership truth; changing them is an admin action, not
 *             a self-service setting)
 *   Security  Send Password Reset Email -> WORKS (same recovery flow
 *             as Forgot Password); Sign Out -> WORKS
 *   Users     Manager/Admin only -> WORKS (UserManagement.tsx)
 *
 * Removed as fake or out-of-scope for v1.1 (owning rails noted):
 * phone / employee ID / default zone inputs (no governed backing),
 * notification preferences (Rail E is CONDITIONAL), theme & density
 * (unimplemented), 2FA (POST-v1.1), active-session count and
 * fabricated session details, fabricated recent-activity feed.
 *
 * In unauthenticated builds (production LotSync today) there is no
 * account to manage -- the page says exactly that instead of
 * pretending.
 */

import { useEffect, useState } from 'react'
import { ROLE_LABELS, useAccess, useMe } from '../auth/AccessProvider'
import { signOut } from '../auth/AuthGate'
import { isAuthEnabled, supabase } from '../auth/supabase'
import { track } from '../observability/analytics'
import UserManagement from './UserManagement'

const USER_ADMIN_ROLES = ['admin', 'manager']
const MAX_DISPLAY_NAME = 60

// ─── Account ─────────────────────────────────────────────────────────────────

function AccountSection() {
  const me = useMe()
  const { refresh } = useAccess()
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)

  useEffect(() => {
    setName(me?.display_name ?? '')
  }, [me?.display_name])

  async function save(e: React.FormEvent) {
    e.preventDefault()
    if (!supabase || busy) return
    const trimmed = name.trim().slice(0, MAX_DISPLAY_NAME)
    setBusy(true)
    setNotice(null)
    // Display name lives in Supabase user_metadata: Auth owns profile
    // identity (no duplicate profile store -- see ACCOUNT_LIFECYCLE.md).
    const { error } = await supabase.auth.updateUser({
      data: { display_name: trimmed || null },
    })
    if (error) {
      setBusy(false)
      setNotice({ kind: 'error', text: 'Could not save your name right now.' })
      return
    }
    // updateUser persists the metadata but the CURRENT access token
    // still carries the old claims until its natural refresh -- and
    // /me reads the verified token. Mint a fresh token now so the
    // saved name is immediately visible (found live in the Sprint 09
    // deployed smoke: "Saved." followed by an empty field).
    await supabase.auth.refreshSession()
    setBusy(false)
    setNotice({ kind: 'ok', text: 'Saved.' })
    // Sprint 11 (analytics): the fact the name changed -- never the
    // name itself.
    track('profile_display_name_updated')
    refresh()
  }

  return (
    <div className="bg-white rounded-xl border border-slate-100 p-5">
      <p className="text-[12px] font-semibold text-slate-600 mb-4">Account</p>
      <form onSubmit={save} className="flex flex-col gap-4">
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 mb-1.5">
            Display Name
          </label>
          <input
            type="text" value={name} maxLength={MAX_DISPLAY_NAME}
            onChange={e => setName(e.target.value)}
            placeholder="How your name appears in DealerDOH"
            className="w-full px-3 py-2 text-[13px] border border-slate-200 rounded-lg bg-white text-slate-800 placeholder:text-slate-300 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all"
          />
        </div>
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 mb-1.5">
            Email
          </label>
          <input
            type="text" value={me?.email ?? ''} readOnly
            className="w-full px-3 py-2 text-[13px] border border-slate-100 rounded-lg bg-slate-50 text-slate-500 cursor-not-allowed"
          />
          <p className="text-[11px] text-slate-400 mt-1">
            Your sign-in email. Contact an administrator to change it.
          </p>
        </div>
        {notice && (
          <div role="alert"
            className={`text-[12px] rounded-lg px-3 py-2 border ${
              notice.kind === 'ok'
                ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                : 'text-red-700 bg-red-50 border-red-200'
            }`}>
            {notice.text}
          </div>
        )}
        <button
          type="submit" disabled={busy}
          className="self-start px-5 py-2 bg-blue-600 text-white text-[13px] font-semibold rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-60">
          {busy ? 'Saving…' : 'Save'}
        </button>
      </form>
    </div>
  )
}

// ─── Access (read-only membership truth) ────────────────────────────────────

function AccessSection() {
  const me = useMe()
  const rows = [
    { label: 'Role', value: me?.role ? (ROLE_LABELS[me.role] ?? me.role) : '—' },
    { label: 'Dealership', value: me?.dealership?.name ?? '—' },
    { label: 'Organization', value: me?.organization?.name ?? '—' },
  ]
  return (
    <div className="bg-white rounded-xl border border-slate-100 p-5">
      <p className="text-[12px] font-semibold text-slate-600 mb-1">Access</p>
      <p className="text-[11px] text-slate-400 mb-4">
        Assigned by your dealership&rsquo;s administrators.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {rows.map(({ label, value }) => (
          <div key={label}>
            <p className="text-[11px] text-slate-400">{label}</p>
            <p className="text-[13px] font-medium text-slate-700 mt-0.5">{value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Security ────────────────────────────────────────────────────────────────

function SecuritySection() {
  const me = useMe()
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)

  async function sendReset() {
    if (!supabase || busy || !me?.email) return
    setBusy(true)
    setNotice(null)
    const { error } = await supabase.auth.resetPasswordForEmail(me.email, {
      redirectTo: `${window.location.origin}/auth/reset-password`,
    })
    setBusy(false)
    setNotice(error
      ? { kind: 'error', text: 'Could not send the email right now. Try again in a moment.' }
      : { kind: 'ok', text: `Password reset instructions sent to ${me.email}.` })
  }

  return (
    <div className="bg-white rounded-xl border border-slate-100 p-5">
      <p className="text-[12px] font-semibold text-slate-600 mb-4">Security</p>
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-[13px] font-semibold text-slate-700">Password</p>
          <p className="text-[11px] text-slate-400 mt-0.5">
            We&rsquo;ll email you a secure link to set a new password.
          </p>
        </div>
        <button
          onClick={() => { void sendReset() }} disabled={busy}
          className="px-3 py-1.5 text-[12px] font-medium border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 transition-colors disabled:opacity-60 flex-shrink-0">
          {busy ? 'Sending…' : 'Send Password Reset Email'}
        </button>
      </div>
      {notice && (
        <div role="alert"
          className={`mt-3 text-[12px] rounded-lg px-3 py-2 border ${
            notice.kind === 'ok'
              ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
              : 'text-red-700 bg-red-50 border-red-200'
          }`}>
          {notice.text}
        </div>
      )}
      <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between gap-4">
        <div>
          <p className="text-[13px] font-semibold text-slate-700">Session</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Sign out of DealerDOH on this device.</p>
        </div>
        <button
          onClick={() => { void signOut() }}
          className="px-3 py-1.5 text-[12px] font-semibold border border-red-200 text-red-600 rounded-lg hover:bg-red-50 transition-colors flex-shrink-0">
          Sign Out
        </button>
      </div>
    </div>
  )
}

// ─── Main ────────────────────────────────────────────────────────────────────

type SectionId = 'account' | 'users'

export default function Profile(): JSX.Element {
  const me = useMe()
  const [activeSection, setActiveSection] = useState<SectionId>('account')

  if (!isAuthEnabled) {
    // Unauthenticated build (production LotSync today): no account
    // exists to manage -- say so instead of rendering fake controls.
    return (
      <div className="h-full flex flex-col bg-slate-50 overflow-hidden">
        <div className="flex-shrink-0 bg-white border-b border-slate-100 px-4 sm:px-6 py-4">
          <h1 className="text-[18px] font-bold text-slate-800">Profile &amp; Settings</h1>
        </div>
        <div className="flex-1 flex items-center justify-center p-6">
          <p className="text-[13px] text-slate-400 text-center max-w-sm">
            Account settings are not available in this deployment — it runs
            without user sign-in.
          </p>
        </div>
      </div>
    )
  }

  const isUserAdmin = USER_ADMIN_ROLES.includes(me?.role ?? '')
  const sections: { id: SectionId; label: string }[] = [
    { id: 'account', label: 'Account & Security' },
    ...(isUserAdmin ? [{ id: 'users' as SectionId, label: 'User Management' }] : []),
  ]

  return (
    <div className="h-full flex flex-col bg-slate-50 overflow-hidden">
      <div className="flex-shrink-0 bg-white border-b border-slate-100 px-4 sm:px-6 py-4">
        <h1 className="text-[18px] font-bold text-slate-800">Profile &amp; Settings</h1>
        <p className="text-[12px] text-slate-400 mt-0.5">
          Your account, access, and security
        </p>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row overflow-y-auto lg:overflow-hidden">
        {sections.length > 1 && (
          <div className="w-full lg:w-48 flex-shrink-0 border-b lg:border-b-0 lg:border-r border-slate-100 bg-white lg:overflow-y-auto py-2 lg:py-3 flex flex-wrap lg:block gap-1 px-2 lg:px-0">
            {sections.map(sec => (
              <button
                key={sec.id}
                onClick={() => setActiveSection(sec.id)}
                className={`w-auto lg:w-full text-left px-3 lg:px-4 py-2 lg:py-2.5 rounded-lg lg:rounded-none text-[13px] font-medium whitespace-nowrap transition-colors ${
                  activeSection === sec.id
                    ? 'text-blue-700 bg-blue-50'
                    : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                {sec.label}
              </button>
            ))}
          </div>
        )}

        <div className="flex-shrink-0 lg:flex-1 lg:overflow-y-auto p-4 sm:p-6">
          <div className="max-w-xl flex flex-col gap-5">
            {activeSection === 'account' && (
              <>
                <AccountSection />
                <AccessSection />
                <SecuritySection />
              </>
            )}
            {activeSection === 'users' && isUserAdmin && <UserManagement />}
          </div>
        </div>
      </div>
    </div>
  )
}
