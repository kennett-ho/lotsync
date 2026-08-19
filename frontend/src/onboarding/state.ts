/**
 * Sprint 12 (Rail B) -- onboarding completion state.
 *
 * Storage decision (ROLE_AWARE_UX.md S12-9): Supabase
 * `user_metadata.dealerdoh_onboarding`, written with the same
 * client `updateUser` mechanism Sprint 09 proved for display_name.
 * Follows the user across devices/browsers, needs NO DealerDOH
 * schema migration and no API change -- unlike display_name it is
 * read client-side from the auth user object, so it never rides
 * token claims and needs no refreshSession() dance.
 *
 * Resilience: every function is a safe no-op without a Supabase
 * client (production's unauthenticated posture -- onboarding simply
 * never exists there) and never throws: onboarding is secondary to
 * operating the product, so a metadata write failing must never
 * block work (Phase 11). Skip records completion too -- a skipped
 * user is a user who chose not to tour, not one to nag; replay
 * stays available from Help forever.
 */

import { supabase } from '../auth/supabase'

export const ONBOARDING_VERSION = 1

export interface OnboardingRecord {
  completed_at: string
  version: number
  skipped: boolean
}

/** The stored record, or null when onboarding has never completed
 * (or auth is disabled, where onboarding does not exist). */
export async function getOnboardingRecord(): Promise<OnboardingRecord | null> {
  if (!supabase) return null
  try {
    const { data, error } = await supabase.auth.getUser()
    if (error || !data.user) return null
    const record = (data.user.user_metadata as Record<string, unknown> | undefined)
      ?.dealerdoh_onboarding as OnboardingRecord | undefined
    return record && typeof record.completed_at === 'string' ? record : null
  } catch {
    return null
  }
}

/** Persist completion (finished or skipped). Returns false on
 * failure -- callers close the tour regardless; worst case it shows
 * once more on another device. */
export async function recordOnboardingComplete(skipped: boolean): Promise<boolean> {
  if (!supabase) return false
  try {
    const record: OnboardingRecord = {
      completed_at: new Date().toISOString(),
      version: ONBOARDING_VERSION,
      skipped,
    }
    const { error } = await supabase.auth.updateUser({
      data: { dealerdoh_onboarding: record },
    })
    return !error
  } catch {
    return false
  }
}
