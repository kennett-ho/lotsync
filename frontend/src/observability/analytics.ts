/**
 * Sprint 11 (Rail F) -- PostHog product analytics: "what are users
 * actually doing?" Explicit events only, initialized ONLY when
 * VITE_POSTHOG_KEY is baked into the build (the browser project token
 * is an intentionally public identifier; a PostHog PERSONAL/admin API
 * key is a secret and must never appear anywhere in this codebase).
 * Unconfigured -> every function below is a silent no-op.
 *
 * Beta privacy posture (OBSERVABILITY.md; each flag explicit so an
 * SDK default change cannot silently widen collection):
 * - autocapture OFF (no click/DOM harvesting)
 * - automatic pageview/pageleave OFF (we send explicit page_viewed
 *   with controlled page identifiers, never raw URLs)
 * - session recording OFF (owner privacy review required to ever
 *   turn it on)
 * - no form capture, no arbitrary DOM text
 * - persistence: localStorage ONLY (Sprint 15) -- the SDK default
 *   'localStorage+cookie' set the app's only cookie; DealerDOH sets
 *   no cookies at all (PRIVACY_ARCHITECTURE.md §4)
 *
 * Sprint 14 (Rail J): the SDK is now loaded with a dynamic import()
 * so its ~235 kB (the single largest bundle contributor) leaves the
 * initial chunk -- telemetry is secondary by doctrine and must never
 * gate first paint. The exported API is unchanged and stays
 * synchronous: calls made before the SDK finishes loading are held in
 * an in-order queue and replayed on readiness, so event ORDER
 * (identify before its tracks, reset severing identity) is preserved
 * exactly. If the SDK fails to load, everything stays a silent no-op
 * -- identical to the unconfigured posture.
 *
 * Identity: the stable internal auth_user_id (a UUID -- non-PII),
 * identified after /me confirms the membership server-side, with
 * role/dealership/organization/environment as person properties.
 * Email and display name are deliberately never sent. signOut()
 * calls resetAnalyticsIdentity() so User B on the same browser never
 * inherits User A's identity.
 *
 * Event taxonomy: OBSERVABILITY.md is canonical. Frontend events are
 * user-intent or UI-observed server outcomes; the structured backend
 * logs remain the authority on what actually happened server-side.
 */

import type { PostHog } from 'posthog-js'
import { OBS_ENVIRONMENT, OBS_RELEASE } from './config'

const env = (import.meta as unknown as { env?: Record<string, string | undefined> }).env ?? {}
const KEY = (env.VITE_POSTHOG_KEY ?? '').trim()
const HOST = (env.VITE_POSTHOG_HOST ?? '').trim() || 'https://us.i.posthog.com'

export const analyticsEnabled = Boolean(KEY)

/** Controlled page identifiers -- the only values page_viewed sends. */
export type PageId =
  | 'dashboard' | 'vehicles' | 'tasks' | 'inventory-sync' | 'profile'
  | 'vehicle-detail' | 'login' | 'reset-password'

// The loaded SDK instance (null until the dynamic import + init
// resolve) and the in-order queue of calls made before that moment.
let client: PostHog | null = null
let pending: Array<(instance: PostHog) => void> | null = []

function withClient(call: (instance: PostHog) => void): void {
  if (client) {
    call(client)
  } else if (pending) {
    pending.push(call)
  }
  // client === null && pending === null -> load failed; drop silently.
}

export function initAnalytics(): void {
  if (!KEY) return
  import('posthog-js')
    .then(({ default: posthog }) => {
      posthog.init(KEY, {
        api_host: HOST,
        autocapture: false,
        capture_pageview: false,
        capture_pageleave: false,
        disable_session_recording: true,
        rageclick: false,
        // Found in deployed DEV verification: the SDK fetches its
        // surveys module from the PostHog CDN by default. No surveys
        // are used -- keep the collection surface (and network) minimal.
        disable_surveys: true,
        // Sprint 15 (Rail L): the SDK default is 'localStorage+cookie',
        // which made this SDK the source of DealerDOH's ONLY cookie (a
        // first-party ph_* identifier cookie -- measured on deployed
        // DEV, 2026-08-20). localStorage alone provides identical
        // identity persistence for a single-origin app, so the cookie
        // is eliminated rather than documented: DealerDOH sets no
        // cookies at all (PRIVACY_ARCHITECTURE.md §4).
        persistence: 'localStorage',
        person_profiles: 'identified_only',
      })
      posthog.register({ environment: OBS_ENVIRONMENT, release: OBS_RELEASE })
      const queued = pending ?? []
      pending = null
      client = posthog
      for (const call of queued) {
        try {
          call(posthog)
        } catch {
          // Telemetry is secondary.
        }
      }
    })
    .catch(() => {
      // SDK failed to load: behave exactly like the unconfigured
      // posture from here on. Telemetry is secondary.
      pending = null
    })
}

export function track(event: string, properties?: Record<string, unknown>): void {
  if (!analyticsEnabled) return
  try {
    withClient(p => p.capture(event, properties))
  } catch {
    // Never let analytics break a workflow.
  }
}

export function identifyAnalyticsUser(
  authUserId: string,
  properties: { role?: string; dealership_id?: string; organization_id?: string },
): void {
  if (!analyticsEnabled || !authUserId) return
  try {
    withClient(p => p.identify(authUserId, {
      role: properties.role,
      dealership_id: properties.dealership_id,
      organization_id: properties.organization_id,
      environment: OBS_ENVIRONMENT,
    }))
  } catch {
    // Telemetry is secondary.
  }
}

/** Called from the single signOut() choke point (auth/AuthGate). */
export function resetAnalyticsIdentity(): void {
  if (!analyticsEnabled) return
  try {
    withClient(p => p.reset())
  } catch {
    // Telemetry is secondary.
  }
}
