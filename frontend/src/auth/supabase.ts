/**
 * Sprint 05 -- the Supabase Auth client, or null.
 *
 * Auth activates ONLY when both VITE_SUPABASE_URL and
 * VITE_SUPABASE_ANON_KEY are baked into the build (the DealerDOH DEV
 * Vercel project sets them; production LotSync sets neither, so its
 * bundle renders exactly the pre-Sprint-05 app with zero auth code
 * paths active). The anon key is public-by-design (it only permits
 * what Supabase Auth itself allows an anonymous browser to do --
 * here: attempt a sign-in); no privileged key ever enters this
 * bundle.
 *
 * supabase-js owns the whole session lifecycle: localStorage
 * persistence (survives refresh), automatic token refresh, and the
 * auth-state events AuthGate subscribes to. This module is the only
 * place the client is constructed.
 */

import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const env =
  (import.meta as unknown as { env?: Record<string, string | undefined> }).env ?? {}

const url = env.VITE_SUPABASE_URL
const anonKey = env.VITE_SUPABASE_ANON_KEY

export const supabase: SupabaseClient | null =
  url && anonKey ? createClient(url, anonKey) : null

export const isAuthEnabled = supabase !== null

/**
 * The current session's access token, for api/client.ts to attach as
 * a Bearer header. Null when auth is disabled (production) or nobody
 * is signed in -- the request then goes out headerless, exactly as
 * before this sprint. getSession() reads the locally persisted
 * session (and supabase-js refreshes it in the background), so this
 * is cheap enough to call per request.
 */
export async function currentAccessToken(): Promise<string | null> {
  if (!supabase) return null
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}
