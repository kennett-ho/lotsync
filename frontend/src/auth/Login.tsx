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

export default function Login() {
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
    // only the failure path needs handling here. Supabase's message
    // for bad credentials is already user-appropriate.
    if (signInError) {
      setError(
        signInError.message === 'Invalid login credentials'
          ? 'Invalid email or password.'
          : signInError.message,
      )
      setSubmitting(false)
    }
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
          </form>

          <div className="text-center text-white/30 text-[11px] mt-6">
            Development accounts are provisioned by an administrator.
          </div>
        </div>
      </div>
    </div>
  )
}
