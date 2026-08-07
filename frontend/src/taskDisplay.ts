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

import type { TaskDTO } from './api/types'

export interface TaskDisplay {
  /** Singular, used on an individual task/detail view. */
  title: string
  /** Plural, used as a Dashboard group header ("Install RecovR Devices"). Falls back to `title` when no natural plural exists. */
  groupTitle: string
  /** One short sentence answering "why am I looking at this" -- no thresholds, rule names, or raw sync wording. */
  description: string
}

const TASK_TYPE_DISPLAY: Record<string, TaskDisplay> = {
  install_recovr_device: {
    title: 'Install RecovR Device',
    groupTitle: 'Install RecovR Devices',
    description: 'Vehicle is in inventory but no paired RecovR device has been detected.',
  },
  install_mdd_beacon: {
    title: 'Install MDD Beacon',
    groupTitle: 'Install MDD Beacons',
    description: 'Vehicle is missing an MDD beacon.',
  },
  investigate_key_for_recovr: {
    title: 'Investigate Key For RecovR',
    groupTitle: 'Investigate Key For RecovR',
    description: 'RecovR device is missing and the key is checked out. Installation is blocked until the key is available.',
  },
  investigate_checked_out_key: {
    title: 'Investigate Checked Out Key',
    groupTitle: 'Investigate Checked Out Keys',
    description: 'Key has been checked out for more than 3 days. Keys are typically returned within 1–2 days.',
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
