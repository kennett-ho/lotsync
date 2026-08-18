/**
 * Sprint 11 (Rail F) -- frontend Sentry: "what is breaking in the
 * browser?" Initializes ONLY when VITE_SENTRY_DSN is baked into the
 * build (a browser DSN is an intentionally public identifier, not a
 * secret -- see OBSERVABILITY.md); without it every capture below is
 * a silent no-op and DealerDOH runs exactly as before Sprint 11.
 *
 * Conservative by construction:
 * - Session Replay is OFF and its integration is never imported.
 *   (In current @sentry/react, replay is opt-in via
 *   Sentry.replayIntegration() -- we add nothing, and the init below
 *   also defensively filters any integration whose name mentions
 *   Replay so a future SDK default cannot silently enable it.)
 * - No performance tracing (tracesSampleRate 0, no browserTracing
 *   integration) until a real need justifies it.
 * - sendDefaultPii false; no user email/display name ever attached --
 *   analytics identity lives in PostHog under the internal
 *   auth_user_id, and Sentry gets nothing user-identifying at all.
 * - Breadcrumb URLs are masked: fetch/xhr breadcrumbs keep origin +
 *   route shape but long identifier-like path segments (VINs are 17
 *   chars) become "*", and query strings are dropped entirely.
 */

import * as Sentry from '@sentry/react'
import { OBS_ENVIRONMENT, OBS_RELEASE, OBS_SERVICE } from './config'

const env = (import.meta as unknown as { env?: Record<string, string | undefined> }).env ?? {}
const DSN = (env.VITE_SENTRY_DSN ?? '').trim()

export const sentryEnabled = Boolean(DSN)

/** Origin + path with identifier-like segments masked; query dropped. */
export function maskUrl(raw: string): string {
  try {
    const url = new URL(raw, window.location.origin)
    const path = url.pathname
      .split('/')
      .map(segment => (/^[A-Za-z0-9_-]{11,}$/.test(segment) ? '*' : segment))
      .join('/')
    return `${url.origin}${path}`
  } catch {
    return '(unparseable-url)'
  }
}

export function initSentry(): void {
  if (!DSN) return
  try {
    Sentry.init({
      dsn: DSN,
      environment: OBS_ENVIRONMENT,
      release: OBS_RELEASE,
      sendDefaultPii: false,
      tracesSampleRate: 0,
      integrations: defaults => defaults.filter(i => !/replay/i.test(i.name)),
      initialScope: { tags: { service: OBS_SERVICE, runtime: 'browser' } },
      beforeBreadcrumb(breadcrumb) {
        if (breadcrumb.category === 'fetch' || breadcrumb.category === 'xhr') {
          if (breadcrumb.data && typeof breadcrumb.data.url === 'string') {
            breadcrumb.data = {
              method: breadcrumb.data.method,
              url: maskUrl(breadcrumb.data.url),
              status_code: breadcrumb.data.status_code,
            }
          }
        }
        return breadcrumb
      },
    })
  } catch {
    // Telemetry is secondary: a bad DSN must not break DealerDOH.
  }
}

/**
 * Report an unexpected error. Returns the Sentry event id ('' when
 * disabled) so UI can show a safe support reference. requestId ties
 * the browser event to the matching backend structured log record.
 */
export function captureUnexpected(error: unknown, requestId?: string): string {
  if (!sentryEnabled) return ''
  try {
    return Sentry.captureException(error, {
      tags: requestId ? { request_id: requestId } : undefined,
    })
  } catch {
    return ''
  }
}
