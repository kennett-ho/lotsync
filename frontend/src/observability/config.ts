/**
 * Sprint 11 (Rails F+G) -- shared observability identity for the
 * frontend: which environment this build serves and which immutable
 * code it is. Structured backend logs, Sentry, and PostHog all use
 * the same two values so events from every layer correlate.
 *
 * Environment: VITE_ENVIRONMENT is the existing deployment variable
 * (Sprint 02's DEV banner reads it). "development" on the DEV Vercel
 * project; a future production train sets "production"; anything else
 * (local vite dev, the current production LotSync build which sets
 * nothing) reports "local" -- where observability is unconfigured and
 * inert anyway.
 *
 * Release: __DEALERDOH_RELEASE__ is a BUILD-TIME constant injected by
 * vite.config.ts from VERCEL_GIT_COMMIT_SHA (Vercel builds) or
 * GITHUB_SHA (CI), falling back to "local-build". A mutable display
 * version is deliberately not used -- observability identifies
 * immutable deployed code.
 */

declare const __DEALERDOH_RELEASE__: string

const env = (import.meta as unknown as { env?: Record<string, string | undefined> }).env ?? {}

const explicit = (env.VITE_ENVIRONMENT ?? '').trim().toLowerCase()

export const OBS_ENVIRONMENT: string =
  explicit === 'development' || explicit === 'production' ? explicit : 'local'

export const OBS_RELEASE: string =
  typeof __DEALERDOH_RELEASE__ === 'string' && __DEALERDOH_RELEASE__
    ? __DEALERDOH_RELEASE__.slice(0, 40)
    : 'unknown'

export const OBS_SERVICE = 'dealerdoh-frontend'
