// Display-only translation from a raw Event row to activity-feed wording.
// UI presentation layer only -- every event_type/source/detail_fields
// combination here is read directly off what sync/reconciler.py already
// persists (see its insert_event call sites); nothing is invented, no
// backend value changes, no new data is required. The event itself
// (event_type, detail_fields, timestamps) is untouched -- this only
// decides what English sentence represents it.
//
// The colored source badge (VehicleDetail.tsx's systemColor/sourceLabel)
// already names which system produced an event, so nothing here repeats
// "Tekion"/"Keyper"/etc. in the title, and nothing repeats the vehicle's
// own stock number -- the user is already looking at this vehicle.

import type { ActivityDTO } from './api/types'

export interface EventDisplay {
  title: string
  /** Secondary, muted line for real technical detail that doesn't belong in the title itself. */
  detail?: string
}

// RapidRecon's Step field has ~77 distinct values with no confirmed
// business meaning for most of them (see sync/reconciler.py's own
// docstrings) -- only these few are established elsewhere in this
// project (WHOLESALE/AT AUCTION exclusion logic, the Archive-step
// "needs review" case). Matched case-insensitively since the raw
// export's casing isn't guaranteed. Anything not listed here still
// gets a natural sentence via the fallback below, just without the
// hand-picked verb phrase.
const RAPIDRECON_STEP_PHRASES: Record<string, string> = {
  'wholesale': 'Marked for wholesale',
  'at auction': 'Sent to auction',
  'archive': 'Archived in RapidRecon',
  'out for sublet': 'Sent for sublet work',
  'inspection': 'In inspection',
}

function describeRapidReconStep(step: unknown): string {
  const raw = typeof step === 'string' ? step.trim() : ''
  if (!raw) return 'Recon status updated'
  const phrase = RAPIDRECON_STEP_PHRASES[raw.toLowerCase()]
  return phrase ?? `Moved to "${raw}"`
}

// pending_identity_resolved's previous_identifier_type is one of the
// three data_quality_exceptions.csv reasons (see reconcile_keyper_tekion) --
// technical classifications, not something to show verbatim.
const IDENTIFIER_TYPE_PHRASES: Record<string, string> = {
  tekion_auto_generated_stock_number: 'an auto-generated stock number',
  unrecognized: 'unrecognized',
  ambiguous_last6_vin_multiple_matches: 'an ambiguous VIN match',
}

function describePreviousIdentifierType(value: unknown): string | undefined {
  if (typeof value !== 'string' || !value) return undefined
  return IDENTIFIER_TYPE_PHRASES[value] ?? value.replace(/_/g, ' ')
}

export function describeEvent(ev: ActivityDTO): EventDisplay {
  const d: Record<string, unknown> = ev.detail_fields ?? {}

  switch (ev.event_type) {
    // ── Tekion ──────────────────────────────────────────────────────
    case 'tekion_observed': {
      const status = typeof d.tekion_status === 'string' ? d.tekion_status : ''
      if (/stock/i.test(status)) return { title: 'Vehicle stocked in' }
      return { title: status ? `Status updated to "${status}"` : 'Vehicle status updated' }
    }
    case 'tekion_sold':
      return { title: 'Vehicle sold' }

    // ── Keyper ──────────────────────────────────────────────────────
    case 'keyper_observed': {
      const status = d.keyper_status
      const soldDate = typeof d.sold_date === 'string' ? d.sold_date : null
      // Same event_type as a normal checkout/return, but this branch
      // (see reconcile_keyper_tekion's sold_key_not_removed_from_keyper
      // case) means a SOLD vehicle's key hasn't been removed from
      // Keyper yet -- a different fact worth its own wording, not a
      // routine check-out/return.
      if (soldDate) {
        return {
          title: status === 'In' ? 'Key still checked in after sale' : 'Key still checked out after sale',
          detail: `Sold ${soldDate}`,
        }
      }
      if (status === 'Out') {
        const daysOut = typeof d.days_out === 'number' ? d.days_out : null
        return {
          title: 'Key checked out',
          detail: daysOut != null ? `${daysOut} day${daysOut === 1 ? '' : 's'} out` : undefined,
        }
      }
      if (status === 'In') return { title: 'Key returned' }
      return { title: 'Key status updated' }
    }
    case 'pending_identity_resolved':
      return {
        title: 'Matched to this vehicle',
        detail: (() => {
          const phrase = describePreviousIdentifierType(d.previous_identifier_type)
          return phrase ? `Previously ${phrase}` : undefined
        })(),
      }

    // ── MDD ─────────────────────────────────────────────────────────
    case 'mdd_observed': {
      // Only "not_paired" is ever actually recorded today (MDD's export
      // is an exceptions-only feed -- see persist_mdd_observations'
      // docstring), but this stays a real switch rather than a single
      // hardcoded string in case that ever changes.
      return { title: d.mdd_status === 'paired' ? 'Beacon paired' : 'Beacon missing' }
    }

    // ── RecovR ──────────────────────────────────────────────────────
    case 'recovr_observed': {
      const status = d.recovr_status
      if (status === 'paired') return { title: 'Device paired' }
      if (status === 'not_paired') return { title: 'Device not paired' }
      return { title: 'RecovR status updated' }
    }

    // ── RapidRecon ──────────────────────────────────────────────────
    case 'rapidrecon_observed':
      return { title: describeRapidReconStep(d.recon_step) }

    // Unknown/future event_type -- degrade gracefully instead of
    // showing nothing. Best-effort strips a leading "Source: " prefix
    // if the raw summary happens to have one, so this fallback doesn't
    // visibly repeat the badge the way the pre-refactor Timeline did.
    default: {
      const raw = ev.summary ?? ev.event_type
      const prefixPattern = new RegExp(`^${ev.source}\\s*:\\s*`, 'i')
      return { title: raw.replace(prefixPattern, '') }
    }
  }
}
