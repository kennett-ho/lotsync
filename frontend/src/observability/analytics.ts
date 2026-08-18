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

import posthog from 'posthog-js'
import { OBS_ENVIRONMENT, OBS_RELEASE } from './config'

const env = (import.meta as unknown as { env?: Record<string, string | undefined> }).env ?? {}
const KEY = (env.VITE_POSTHOG_KEY ?? '').trim()
const HOST = (env.VITE_POSTHOG_HOST ?? '').trim() || 'https://us.i.posthog.com'

export const analyticsEnabled = Boolean(KEY)

/** Controlled page identifiers -- the only values page_viewed sends. */
export type PageId =
  | 'dashboard' | 'vehicles' | 'tasks' | 'inventory-sync' | 'profile'
  | 'vehicle-detail' | 'login' | 'reset-password'

export function initAnalytics(): void {
  if (!KEY) return
  try {
    posthog.init(KEY, {
      api_host: HOST,
      autocapture: false,
      capture_pageview: false,
      capture_pageleave: false,
      disable_session_recording: true,
      rageclick: false,
      person_profiles: 'identified_only',
    })
    posthog.register({ environment: OBS_ENVIRONMENT, release: OBS_RELEASE })
  } catch {
    // Telemetry is secondary.
  }
}

export function track(event: string, properties?: Record<string, unknown>): void {
  if (!analyticsEnabled) return
  try {
    posthog.capture(event, properties)
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
    posthog.identify(authUserId, {
      role: properties.role,
      dealership_id: properties.dealership_id,
      organization_id: properties.organization_id,
      environment: OBS_ENVIRONMENT,
    })
  } catch {
    // Telemetry is secondary.
  }
}

/** Called from the single signOut() choke point (auth/AuthGate). */
export function resetAnalyticsIdentity(): void {
  if (!analyticsEnabled) return
  try {
    posthog.reset()
  } catch {
    // Telemetry is secondary.
  }
}
