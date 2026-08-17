/**
 * Sprint 09 -- the password recovery / invite acceptance page, served
 * at /auth/reset-password (routed by main.tsx BEFORE the auth gate:
 * this flow must work from a fresh browser with no operational
 * session, which is exactly how an emailed link arrives).
 *
 * How a person lands here:
 *   - "Forgot password?" on the login screen ->
 *     supabase.auth.resetPasswordForEmail(email, {redirectTo: THIS
 *     page}) -> Supabase emails a recovery link -> link verifies at
 *     Supabase -> redirect lands here carrying recovery tokens
 *   - Manager/Admin invite (POST /users/invite) -> GoTrue invite email
 *     -> same landing, type=invite -- setting a first password and
 *     resetting one are deliberately the same page.
 *
 * supabase-js (detectSessionInUrl, its default) consumes the tokens
 * from the URL on load and emits SIGNED_IN / PASSWORD_RECOVERY; from
 * that moment a recovery session exists and the new-password form is
 * shown. A malformed, expired, or missing token produces NO session --
 * the page shows a safe dead-end with a path back to login, and the
 * operational app never mounts on this route regardless.
 *
 * Session policy after a successful password set (documented in
 * ACCOUNT_LIFECYCLE.md): updateUser({password}) then
 * signOut({scope: 'global'}) -- Supabase revokes every refresh token
 * for the user, so other devices' sessions die at their next refresh
 * (the strongest revocation the provider supports; access tokens
 * already issued live only until their short expiry). The person then
 * signs in fresh with the new password.
 *
 * Passwords never touch logs, analytics, or state beyond these two
 * controlled inputs.
 */

import { useEffect, useState } from 'react'
import { supabase } from './supabase'

type Phase =
  | 'checking'    // waiting for supabase-js to consume URL tokens
  | 'ready'       // recovery session present -- show the form
  | 'invalid'     // no/expired/malformed token -- safe dead end
  | 'submitting'
  | 'done'        // password set; sessions revoked; back-to-login CTA

const MIN_PASSWORD_LENGTH = 8

export default function ResetPassword() {
  const [phase, setPhase] = useState<Phase>('checking')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!supabase) {
      setPhase('invalid')
      return
    }
    // Supabase appends explicit error params when a link is expired or
    // already used -- treat that as invalid immediately (and never
    // render provider text to the user).
    const hash = new URLSearchParams(window.location.hash.replace(/^#/, ''))
    if (hash.get('error') || new URLSearchParams(window.location.search).get('error')) {
      setPhase('invalid')
      return
    }

    let settled = false
    const finish = (ok: boolean) => {
      if (!settled) {
        settled = true
        setPhase(ok ? 'ready' : 'invalid')
      }
    }

    const { data: subscription } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'PASSWORD_RECOVERY' || (event === 'SIGNED_IN' && session)) finish(true)
    })
    // detectSessionInUrl work happens during getSession()'s init; poll
    // once after it settles. A short grace period covers the token
    // exchange; beyond it, no session means no valid link.
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) finish(true)
      else setTimeout(() => { void supabase.auth.getSession().then(({ data: again }) => finish(!!again.session)) }, 1500)
    })
    return () => subscription.subscription.unsubscribe()
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!supabase || phase === 'submitting') return
    setError(null)
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`)
      return
    }
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    setPhase('submitting')
    const { error: updateError } = await supabase.auth.updateUser({ password })
    if (updateError) {
      // Supabase messages here are user-appropriate ("should be
      // different from the old password", weak password, etc.) and
      // contain no token material.
      setError(updateError.message)
      setPhase('ready')
      return
    }
    // Session policy: revoke everything, everywhere, then require a
    // fresh sign-in with the new password.
    await supabase.auth.signOut({ scope: 'global' })
    setPassword('')
    setConfirm('')
    setPhase('done')
  }

  function backToLogin() {
    window.location.assign('/')
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#0B1220' }}>
      <div className="w-full text-center py-1.5 text-[11px] font-bold tracking-wide text-white"
           style={{ backgroundColor: '#7C3AED' }}>
        DealerDOH DEV — Development Environment — Synthetic/Test Data Only
      </div>
      <div className="flex-1 flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <div className="text-white text-2xl font-bold tracking-tight">DealerDOH</div>
            <div className="text-white/50 text-[13px] mt-1">Set your password</div>
          </div>

          {phase === 'checking' && (
            <div className="text-center text-white/40 text-[13px]">Checking your link…</div>
          )}

          {phase === 'invalid' && (
            <div className="rounded-xl p-6 border border-white/10 text-center"
                 style={{ backgroundColor: '#111B2E' }}>
              <div className="text-white text-[14px] font-semibold mb-2">
                This link is invalid or has expired
              </div>
              <p className="text-white/50 text-[12px] mb-5">
                Password links can only be used once and expire after a short
                time. You can request a new one from the sign-in screen.
              </p>
              <button onClick={backToLogin}
                className="w-full rounded-md py-2.5 text-[13px] font-semibold text-white"
                style={{ backgroundColor: '#1D4ED8' }}>
                Back to Sign In
              </button>
            </div>
          )}

          {(phase === 'ready' || phase === 'submitting') && (
            <form onSubmit={handleSubmit}
                  className="rounded-xl p-6 space-y-4 border border-white/10"
                  style={{ backgroundColor: '#111B2E' }}>
              <label className="block">
                <span className="text-white/70 text-[12px] font-semibold">New password</span>
                <input
                  type="password" required autoComplete="new-password" value={password}
                  onChange={e => setPassword(e.target.value)}
                  minLength={MIN_PASSWORD_LENGTH}
                  className="mt-1.5 w-full rounded-md px-3 py-2 text-[13px] text-white placeholder-white/30 border border-white/10 outline-none focus:border-blue-500"
                  style={{ backgroundColor: '#0B1220' }}
                  placeholder={`At least ${MIN_PASSWORD_LENGTH} characters`}
                />
              </label>
              <label className="block">
                <span className="text-white/70 text-[12px] font-semibold">Confirm new password</span>
                <input
                  type="password" required autoComplete="new-password" value={confirm}
                  onChange={e => setConfirm(e.target.value)}
                  minLength={MIN_PASSWORD_LENGTH}
                  className="mt-1.5 w-full rounded-md px-3 py-2 text-[13px] text-white placeholder-white/30 border border-white/10 outline-none focus:border-blue-500"
                  style={{ backgroundColor: '#0B1220' }}
                  placeholder="Repeat the password"
                />
              </label>

              {error && (
                <div className="text-[12px] rounded-md px-3 py-2 border border-red-500/30 text-red-300"
                     style={{ backgroundColor: 'rgba(127,29,29,0.25)' }} role="alert">
                  {error}
                </div>
              )}

              <button
                type="submit" disabled={phase === 'submitting'}
                className="w-full rounded-md py-2.5 text-[13px] font-semibold text-white transition-opacity disabled:opacity-60"
                style={{ backgroundColor: '#1D4ED8' }}>
                {phase === 'submitting' ? 'Saving…' : 'Set Password'}
              </button>
            </form>
          )}

          {phase === 'done' && (
            <div className="rounded-xl p-6 border border-white/10 text-center"
                 style={{ backgroundColor: '#111B2E' }}>
              <div className="text-emerald-300 text-[14px] font-semibold mb-2">
                Password updated
              </div>
              <p className="text-white/50 text-[12px] mb-5">
                For security, you have been signed out everywhere. Sign in with
                your new password to continue.
              </p>
              <button onClick={backToLogin}
                className="w-full rounded-md py-2.5 text-[13px] font-semibold text-white"
                style={{ backgroundColor: '#1D4ED8' }}>
                Back to Sign In
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
