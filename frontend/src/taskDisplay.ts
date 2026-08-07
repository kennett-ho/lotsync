// Display-only translation from a raw Task row to dispatcher-facing
// wording, mirroring eventDisplay.ts's philosophy for Vehicle Detail's
// Timeline. task_type is a small, stable backend enum (see
// sync/reconciler.py's "Task-generation philosophy" block -- currently
// exactly four values), so title/description are keyed directly off
// it rather than parsed out of Task.reason, which is free-text meant
// for audit/debugging, not end-user display -- and was the actual
// source of the "nan days" text dealership staff were seeing (root
// cause fixed in sync/reconciler.py; sanitize() below is a frontend
// safety net on top of that, not a substitute for it).
//
// Descriptions answer "why is this work on today's queue," not "what
// business rule created this" -- no thresholds, standing-policy names,
// reconciliation/sync terminology, or "generated because" phrasing.

import type { TaskDTO } from './api/types'

export interface TaskDisplay {
  /** Singular, used on an individual task/detail view. */
  title: string
  /** Plural, used as a Dashboard group header ("Install RecovR Devices"). Falls back to `title` when no natural plural exists. */
  groupTitle: string
  /** One short sentence answering "why is this work on today's queue" -- no thresholds, rule names, or raw sync wording. */
  description: string
}

// Subject-free on purpose ("Waiting for..." not "These vehicles are
// waiting for..."): describeTask() is shared between the Dashboard
// group header (describing many vehicles at once) and Vehicle Detail's
// per-task card (describing one task on the vehicle already on screen)
// -- a "these vehicles"/"this vehicle" subject would read naturally in
// only one of those two places. Dropping the subject entirely reads
// correctly in both.
const TASK_TYPE_DISPLAY: Record<string, TaskDisplay> = {
  install_recovr_device: {
    title: 'Install RecovR Device',
    groupTitle: 'Install RecovR Devices',
    description: 'Waiting for a RecovR installation.',
  },
  install_mdd_beacon: {
    title: 'Install MDD Beacon',
    groupTitle: 'Install MDD Beacons',
    description: 'Missing an MDD beacon.',
  },
  investigate_key_for_recovr: {
    title: 'Investigate Key For RecovR',
    groupTitle: 'Investigate Key For RecovR',
    description: 'RecovR device is missing, and the key is checked out, which is blocking installation.',
  },
  investigate_checked_out_key: {
    title: 'Investigate Checked Out Key',
    groupTitle: 'Investigate Checked Out Keys',
    description: 'Key has been checked out longer than expected.',
  },
}

function humanizeTaskType(taskType: string): string {
  const words = taskType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  return words.replace(/\bRecovr\b/, 'RecovR').replace(/\bMdd\b/, 'MDD')
}

// Never let a raw NaN/None/undefined/null token reach the screen,
// whatever produced it -- a frontend backstop, not where the real fix
// belongs (see sync/reconciler.py's days_out normalization for that).
function sanitize(text: string): string {
  return text.replace(/\b(nan|none|undefined|null)\b/gi, '').replace(/\s{2,}/g, ' ').trim()
}

export function describeTask(t: TaskDTO): TaskDisplay {
  const known = TASK_TYPE_DISPLAY[t.task_type]
  if (known) return known
  // Unknown/future task_type -- degrade gracefully instead of
  // rendering nothing, same contract as eventDisplay.ts's default case.
  const title = humanizeTaskType(t.task_type)
  return {
    title,
    groupTitle: title,
    description: t.reason ? sanitize(t.reason) : 'No additional detail recorded.',
  }
}

// Per-vehicle operational detail line for an expanded task row (e.g.
// "Key checked out 4 days ago"). Only the two Keyper-involving task
// types have a per-vehicle number worth surfacing this way; the two
// install task types have nothing that varies vehicle-to-vehicle
// beyond what the group description already says, so they intentionally
// get no line here rather than a duplicated/invented one.
//
// This is the one place in the frontend that still reads Task.reason
// for a KNOWN task_type -- there's no structured field for "how many
// days" on TaskDTO (Task.reason is the only place it lives), so this
// is presentation-layer parsing of already-clean text (post the
// sync/reconciler.py NaN fix), not a new coupling to raw sync wording.
// Matches only "<digits> day(s)" with a space (e.g. "4 days"), which
// deliberately does not match the hyphenated "3-day investigate
// threshold" phrase also present in investigate_checked_out_key's
// reason text -- that's rule wording, never surfaced here.
function parseDaysOut(reason: string | null): number | null {
  if (!reason) return null
  const match = reason.match(/(\d+)\s+days?\b/i)
  return match ? parseInt(match[1], 10) : null
}

export function describeTaskDetail(t: TaskDTO): string | undefined {
  if (t.task_type !== 'investigate_checked_out_key' && t.task_type !== 'investigate_key_for_recovr') return undefined
  const days = parseDaysOut(t.reason)
  if (days == null) return undefined
  return `Key checked out ${days} day${days === 1 ? '' : 's'} ago`
}
