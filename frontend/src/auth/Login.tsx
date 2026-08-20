/**
 * Sprint 05 -- the DealerDOH DEV sign-in screen. Rendered by AuthGate
 * whenever auth is enabled and no session exists; the operational app
 * is never mounted unauthenticated. Deliberately minimal per the
 * sprint spec: email, password, sign in, loading state, clear failure
 * state -- no signup (dev users are admin-provisioned; Supabase
 * public signups are disabled), no password-reset UX beyond what
 * Supabase provides, no role selection of any kind.
 */

import { useState } from 'react'
import { supabase } from './supabase'
import { track } from '../observability/analytics'

// Sprint 09: the recovery request is deliberately enumeration-safe --
// the SAME generic confirmation renders whether or not an account
// exists for the address (Supabase's endpoint itself succeeds either
// way; nothing in this UI distinguishes the cases).
const FORGOT_SENT_MESSAGE =
  'If an account exists for that email, password recovery instructions have been sent.'

export default function Login() {
  const [mode, setMode] = useState<'signin' | 'forgot' | 'forgot-sent'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!supabase || submitting) return
    setSubmitting(true)
    setError(null)
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    })
    // On success AuthGate's onAuthStateChange unmounts this screen;
    // only the failure path needs handling here. Sprint 13 (F5): every
    // sign-in failure collapses to ONE generic message so the screen
    // never reveals account state ("Email not confirmed", "user
    // disabled", etc. all leak account existence and undercut the
    // enumeration-safe recovery flow). The one exception is a genuine
    // rate-limit notice, which reveals nothing about the account and
    // tells the person to wait -- same carve-out the recovery path uses.
    if (signInError) {
      setError(
        /security purposes|rate limit|seconds/i.test(signInError.message)
          ? signInError.message
          : 'Invalid email or password.',
      )
      setSubmitting(false)
    }
  }

  async function handleForgot(e: React.FormEvent) {
    e.preventDefault()
    if (!supabase || submitting) return
    setSubmitting(true)
    setError(null)
    const { error: resetError } = await supabase.auth.resetPasswordForEmail(
      email.trim(),
      { redirectTo: `${window.location.origin}/auth/reset-password` },
    )
    setSubmitting(false)
    if (resetError) {
      // Rate-limit wording from Supabase is user-appropriate and
      // reveals nothing about the account; anything else gets a
      // generic retry line (never a provider error dump).
      setError(
        /security purposes|rate limit|seconds/i.test(resetError.message)
          ? resetError.message
          : 'Could not send the email right now. Please try again in a moment.',
      )
      return
    }
    // Sprint 11 (analytics): the fact a recovery was requested --
    // deliberately WITHOUT the entered email (taxonomy rule).
    track('password_recovery_requested')
    setMode('forgot-sent')
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
            <div className="text-white/50 text-[13px] mt-1">
              Sign in to the development dealership
            </div>
          </div>

          {mode === 'signin' && (
            <form onSubmit={handleSubmit}
                  className="rounded-xl p-6 space-y-4 border border-white/10"
                  style={{ backgroundColor: '#111B2E' }}>
              <label className="block">
                <span className="text-white/70 text-[12px] font-semibold">Email</span>
                <input
                  type="email" required autoComplete="username" value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="mt-1.5 w-full rounded-md px-3 py-2 text-[13px] text-white placeholder-white/30 border border-white/10 outline-none focus:border-blue-500"
                  style={{ backgroundColor: '#0B1220' }}
                  placeholder="you@qa.dealerdoh.example"
                />
              </label>
              <label className="block">
                <span className="text-white/70 text-[12px] font-semibold">Password</span>
                <input
                  type="password" required autoComplete="current-password" value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="mt-1.5 w-full rounded-md px-3 py-2 text-[13px] text-white placeholder-white/30 border border-white/10 outline-none focus:border-blue-500"
                  style={{ backgroundColor: '#0B1220' }}
                  placeholder="••••••••"
                />
              </label>

              {error && (
                <div className="text-[12px] rounded-md px-3 py-2 border border-red-500/30 text-red-300"
                     style={{ backgroundColor: 'rgba(127,29,29,0.25)' }} role="alert">
                  {error}
                </div>
              )}

              <button
                type="submit" disabled={submitting}
                className="w-full rounded-md py-2.5 text-[13px] font-semibold text-white transition-opacity disabled:opacity-60"
                style={{ backgroundColor: '#1D4ED8' }}>
                {submitting ? 'Signing in…' : 'Sign In'}
              </button>

              <div className="text-center pt-1">
                <button type="button"
                  onClick={() => { setError(null); setMode('forgot') }}
                  className="text-[12px] text-white/50 hover:text-white/80 transition-colors underline underline-offset-2">
                  Forgot password?
                </button>
              </div>
            </form>
          )}

          {mode === 'forgot' && (
            <form onSubmit={handleForgot}
                  className="rounded-xl p-6 space-y-4 border border-white/10"
                  style={{ backgroundColor: '#111B2E' }}>
              <div className="text-white/70 text-[12px]">
                Enter your email and we&rsquo;ll send password recovery
                instructions.
              </div>
              <label className="block">
                <span className="text-white/70 text-[12px] font-semibold">Email</span>
                <input
                  type="email" required autoComplete="username" value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="mt-1.5 w-full rounded-md px-3 py-2 text-[13px] text-white placeholder-white/30 border border-white/10 outline-none focus:border-blue-500"
                  style={{ backgroundColor: '#0B1220' }}
                  placeholder="you@qa.dealerdoh.example"
                />
              </label>

              {error && (
                <div className="text-[12px] rounded-md px-3 py-2 border border-red-500/30 text-red-300"
                     style={{ backgroundColor: 'rgba(127,29,29,0.25)' }} role="alert">
                  {error}
                </div>
              )}

              <button
                type="submit" disabled={submitting}
                className="w-full rounded-md py-2.5 text-[13px] font-semibold text-white transition-opacity disabled:opacity-60"
                style={{ backgroundColor: '#1D4ED8' }}>
                {submitting ? 'Sending…' : 'Send Recovery Email'}
              </button>

              <div className="text-center pt-1">
                <button type="button"
                  onClick={() => { setError(null); setMode('signin') }}
                  className="text-[12px] text-white/50 hover:text-white/80 transition-colors underline underline-offset-2">
                  Back to sign in
                </button>
              </div>
            </form>
          )}

          {mode === 'forgot-sent' && (
            <div className="rounded-xl p-6 border border-white/10 text-center"
                 style={{ backgroundColor: '#111B2E' }}>
              <div className="text-emerald-300 text-[13px] font-semibold mb-2">
                Check your email
              </div>
              <p className="text-white/60 text-[12px] mb-5">{FORGOT_SENT_MESSAGE}</p>
              <button
                onClick={() => { setError(null); setMode('signin') }}
                className="w-full rounded-md py-2.5 text-[13px] font-semibold text-white"
                style={{ backgroundColor: '#1D4ED8' }}>
                Back to Sign In
              </button>
            </div>
          )}

          <div className="text-center text-white/30 text-[11px] mt-6">
            Development accounts are provisioned by an administrator.
          </div>
        </div>
      </div>
    </div>
  )
}
