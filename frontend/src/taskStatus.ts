// Display-only label mapping for Task.commitment_standing/execution_status.
// UI terminology layer only -- the underlying backend values (outstanding/
// honored/moot/cancelled/superseded; not_started/in_progress/blocked/
// completed) are never written back, matching Tasks.tsx's existing
// "never collapsed back into one" convention. See models/task.py,
// DATA_MODEL.md for what these values actually mean.
//
// Shared by Tasks.tsx and VehicleDetail.tsx so the two screens can't
// silently drift to different wording for the same backend value.

import type { TaskDTO } from './api/types'

export type StatusTone = 'slate' | 'blue' | 'amber' | 'green'

const COMMITMENT_LABELS: Record<string, string> = {
  outstanding: 'Open',
  honored: 'Completed',
  moot: 'No Longer Needed',
  cancelled: 'Cancelled',
  superseded: 'Replaced',
}

export function commitmentStandingLabel(standing: string): string {
  return COMMITMENT_LABELS[standing] ?? standing
}

export function taskStatusDisplay(t: TaskDTO): { label: string; tone: StatusTone } {
  switch (t.commitment_standing) {
    case 'honored':    return { label: COMMITMENT_LABELS.honored, tone: 'green' }
    case 'moot':       return { label: COMMITMENT_LABELS.moot, tone: 'slate' }
    case 'cancelled':  return { label: COMMITMENT_LABELS.cancelled, tone: 'slate' }
    case 'superseded': return { label: COMMITMENT_LABELS.superseded, tone: 'slate' }
    default:
      switch (t.execution_status) {
        case 'not_started': return { label: COMMITMENT_LABELS.outstanding, tone: 'slate' }
        case 'in_progress':  return { label: 'In Progress', tone: 'blue' }
        case 'blocked':      return { label: 'Blocked', tone: 'amber' }
        case 'completed':    return { label: 'Waiting Verification', tone: 'amber' }
        default:             return { label: t.execution_status, tone: 'slate' }
      }
  }
}
