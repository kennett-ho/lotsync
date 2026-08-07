// Tasks.tsx — Operational dispatch board
//
// Sprint 3 (Frontend Integration): this is the one screen this sprint's
// own kickoff explicitly deferred until last, specifically because the
// mockup's single collapsed `status` field
// (outstanding|in-progress|waiting-verification|verified|cancelled|superseded)
// re-fuses what the backend deliberately split during the Pre-Sprint 4
// design review (DATA_MODEL.md's Task entry, DECISION_FRAMEWORK.md) --
// Architectural Risk #1 in FRONTEND_BACKEND_RECONCILIATION.md. That
// correction happens here, then the screen is wired to GET /tasks.
//
// What changed relative to the mockup, and why (full detail in
// PHASE_3_SPRINT_3_REVIEW.md):
// - `commitment_standing` and `execution_status` are now two
//   independent, always-separately-rendered fields, never collapsed
//   back into one. `deriveDisplayStatus` below computes a label from
//   both for convenience, but nothing is ever written back into a
//   single stored field.
// - Tasks are grouped by `task_type` for the card list -- DATA_MODEL.md
//   is explicit that "Install RecovR Devices, 6 tasks" is six separate,
//   one-vehicle Task rows aggregated for display, never a single Task
//   with a vehicle list. The mockup's mock data had this backwards
//   (one Task object holding a `vehicles: TaskVehicle[]` array); real
//   TaskDTO is one-vehicle-one-task, per DATA_MODEL.md.
// - The mockup's `reason` (a structured pass/fail checklist) has no
//   backend equivalent -- `Task.reason` is a free-text string. Shown
//   as-is rather than reconstructed into fabricated checks.
// - The mockup's per-task `checklist` and `timeline` (multi-step
//   activity log) have no backend equivalent either: there's no
//   endpoint exposing TaskExecutionEvent history, and Task has no
//   discrete sub-step list. Dropped rather than fabricated; only the
//   two real timestamps available (`created_at`, `completed_at`) are
//   shown.
// - Start/Pause/Mark Complete/Cancel are disabled ("Coming soon") --
//   this sprint explicitly excludes write APIs, so no button silently
//   mutates local state that doesn't reflect the backend.
// - "My Tasks" filters against a placeholder employee id (CURRENT_EMPLOYEE_ID
//   below) -- there is no real authentication yet (Phase 3's own named
//   gate, still unstarted), so this stands in until a logged-in user's
//   employee id is available from somewhere real.
// - "Automated" vs. "Management Requests" is now driven by the real
//   `ratification_type` field (`standing_policy`/null vs. `human`)
//   rather than a fabricated `TaskSource` union with no backend
//   equivalent.

import { useMemo, useState } from 'react'
import { getTasks } from '../api/tasks'
import { useApi } from '../api/useApi'
import { isBackendUnavailable } from '../api/client'
import type { TaskDTO } from '../api/types'

// Placeholder for "the current user" until Phase 3 authentication
// exists -- matches the rest of this prototype's hardcoded identity.
const CURRENT_EMPLOYEE_ID = 'emp-0142'

const DEPARTMENTS = ['Inventory', 'Controller', 'Lot Ops', 'Dealer Trades']
const PRIORITIES = ['Critical', 'High', 'Medium', 'Low']
const PRIORITY_RANK: Record<string, number> = { Critical: 0, High: 1, Medium: 2, Low: 3 }

function humanize(taskType: string): string {
  const words = taskType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  return words.replace(/\bRecovr\b/, 'RecovR').replace(/\bMdd\b/, 'MDD')
}

// ─── Display-status derivation (read-only; never written back) ────────────────

type Tone = 'slate' | 'blue' | 'amber' | 'green'

function deriveDisplayStatus(t: TaskDTO): { label: string; tone: Tone } {
  switch (t.commitment_standing) {
    case 'honored':    return { label: 'Honored', tone: 'green' }
    case 'moot':       return { label: 'Moot', tone: 'slate' }
    case 'cancelled':  return { label: 'Cancelled', tone: 'slate' }
    case 'superseded': return { label: 'Superseded', tone: 'slate' }
    default:
      switch (t.execution_status) {
        case 'not_started': return { label: 'Outstanding', tone: 'slate' }
        case 'in_progress':  return { label: 'In Progress', tone: 'blue' }
        case 'blocked':      return { label: 'Blocked', tone: 'amber' }
        case 'completed':    return { label: 'Waiting Verification', tone: 'amber' }
        default:             return { label: t.execution_status, tone: 'slate' }
      }
  }
}

const toneClasses: Record<Tone, string> = {
  slate: 'text-slate-400',
  blue: 'text-blue-600 font-semibold',
  amber: 'text-amber-600 font-semibold',
  green: 'text-emerald-600 font-semibold',
}

const priorityBadge: Record<string, { stripe: string; badge: string }> = {
  Critical: { stripe: 'bg-red-500',    badge: 'bg-red-100 text-red-700 border border-red-200' },
  High:     { stripe: 'bg-orange-400', badge: 'bg-orange-100 text-orange-700 border border-orange-200' },
  Medium:   { stripe: 'bg-amber-400',  badge: 'bg-amber-50 text-amber-700 border border-amber-200' },
  Low:      { stripe: 'bg-slate-300',  badge: 'bg-slate-100 text-slate-500 border border-slate-200' },
}

function ratificationLabel(t: TaskDTO): string {
  return t.ratification_type === 'human' ? 'Ratified by Person' : 'Standing Policy'
}

function isCompletedToday(t: TaskDTO): boolean {
  if (t.commitment_standing === 'outstanding' || !t.completed_at) return false
  const d = new Date(t.completed_at)
  const now = new Date()
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate()
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

type QueueFilter = 'all' | 'my' | 'standing-policy' | 'human-ratified' | 'verification' | 'completed-today'
type SidebarFilter =
  | { type: 'queue'; value: QueueFilter }
  | { type: 'department'; value: string }
  | { type: 'priority'; value: string }

function matchesFilter(t: TaskDTO, f: SidebarFilter): boolean {
  if (f.type === 'queue') {
    switch (f.value) {
      case 'all':              return true
      case 'my':                return t.assigned_employee_id === CURRENT_EMPLOYEE_ID
      case 'standing-policy':   return t.ratification_type !== 'human'
      case 'human-ratified':    return t.ratification_type === 'human'
      case 'verification':      return t.commitment_standing === 'outstanding' && t.execution_status === 'completed'
      case 'completed-today':   return isCompletedToday(t)
    }
  }
  if (f.type === 'department') return t.department === f.value
  if (f.type === 'priority')   return t.priority === f.value
  return true
}

function Sidebar({ tasks, filter, onFilter }: { tasks: TaskDTO[]; filter: SidebarFilter; onFilter: (f: SidebarFilter) => void }) {
  const cnt = (f: SidebarFilter) => tasks.filter(t => matchesFilter(t, f)).length
  const active = (f: SidebarFilter) => JSON.stringify(filter) === JSON.stringify(f)

  function Btn({ label, f, warn }: { label: string; f: SidebarFilter; warn?: boolean }) {
    const c = cnt(f)
    const on = active(f)
    return (
      <button onClick={() => onFilter(f)}
        className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all ${
          on ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
        }`}>
        {label}
        {c > 0 && (
          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
            on ? 'bg-white/20' : warn ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-500'
          }`}>{c}</span>
        )}
      </button>
    )
  }

  const section = (label: string) => (
    <div className="text-[9px] font-bold uppercase tracking-widest text-slate-400 px-3 pt-4 pb-1">{label}</div>
  )

  // Demo Polish: department/priority are real Task columns, but nothing
  // populates them today (Slice 5's auto-generated install tasks never
  // set department, and no rule assigns priority yet -- see
  // queries/dashboard.py's task_counts_by_department docstring). A
  // filter button that can only ever show "0 tasks" is worse than no
  // button -- it invites a click that looks broken. Only show the ones
  // that can currently return something; the section itself disappears
  // once nothing in it can match. Fully data-driven, so both reappear
  // automatically the moment real values start showing up.
  const availableDepartments = DEPARTMENTS.filter(d => cnt({ type: 'department', value: d }) > 0)
  const availablePriorities = PRIORITIES.filter(p => cnt({ type: 'priority', value: p }) > 0)

  return (
    <aside className="flex-shrink-0 w-48 bg-white border-r border-slate-200 flex flex-col py-3 overflow-y-auto" style={{ scrollbarWidth: 'none' }}>
      {section('Queue')}
      <div className="px-2 space-y-0.5">
        <Btn label="All Tasks"           f={{ type: 'queue', value: 'all' }} />
        <Btn label="My Tasks"            f={{ type: 'queue', value: 'my' }} />
        <Btn label="Standing Policy"     f={{ type: 'queue', value: 'standing-policy' }} />
        <Btn label="Ratified by Person"  f={{ type: 'queue', value: 'human-ratified' }} />
        <Btn label="Verification Needed" f={{ type: 'queue', value: 'verification' }} warn />
        <Btn label="Completed Today"     f={{ type: 'queue', value: 'completed-today' }} />
      </div>

      {availableDepartments.length > 0 && (
        <>
          {section('Department')}
          <div className="px-2 space-y-0.5">
            {availableDepartments.map(d => (
              <Btn key={d} label={d} f={{ type: 'department', value: d }} />
            ))}
          </div>
        </>
      )}

      {availablePriorities.length > 0 && (
        <>
          {section('Priority')}
          <div className="px-2 space-y-0.5">
            {availablePriorities.map(p => (
              <Btn key={p} label={p} f={{ type: 'priority', value: p }} />
            ))}
          </div>
        </>
      )}
    </aside>
  )
}

// ─── Task-type group card ───────────────────────────────────────────────────────

interface TaskTypeGroup { taskType: string; tasks: TaskDTO[] }

function GroupCard({ group, onSelectTask, onVehicleSelect }: {
  group: TaskTypeGroup; onSelectTask: (id: number) => void; onVehicleSelect: (vin: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const isMulti = group.tasks.length > 1
  const single = !isMulti ? group.tasks[0] : null

  const topPriority = group.tasks
    .map(t => t.priority)
    .filter((p): p is string => p !== null)
    .sort((a, b) => (PRIORITY_RANK[a] ?? 99) - (PRIORITY_RANK[b] ?? 99))[0]
  const pb = priorityBadge[topPriority ?? 'Low']
  const doneCount = group.tasks.filter(t => t.commitment_standing !== 'outstanding').length

  return (
    <div className="bg-white border border-slate-200 hover:border-slate-300 rounded-xl overflow-hidden transition-all duration-150">
      <div className="flex">
        <div className={`w-1 flex-shrink-0 ${pb.stripe}`} />
        <div className="flex-1 px-4 py-3 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <div className="flex items-center gap-2">
              {topPriority && (
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide ${pb.badge}`}>{topPriority}</span>
              )}
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200">
                {ratificationLabel(group.tasks[0])}
              </span>
            </div>
            {single && (
              <span className={`text-[10px] font-medium flex-shrink-0 ${toneClasses[deriveDisplayStatus(single).tone]}`}>
                {deriveDisplayStatus(single).label}
              </span>
            )}
          </div>

          <div className="flex items-start justify-between gap-3 mb-1.5">
            <h3 className="text-[14px] font-bold text-slate-900 leading-snug">{humanize(group.taskType)}</h3>
            {isMulti && (
              <button onClick={() => setExpanded(e => !e)}
                className="flex-shrink-0 flex items-center gap-1 text-[10px] font-bold text-slate-500 bg-slate-100 hover:bg-slate-200 border border-slate-200 px-2 py-0.5 rounded-full transition-colors">
                {group.tasks.length} Vehicles
                <span className="text-slate-400 font-normal">· {doneCount}/{group.tasks.length}</span>
                <svg width="9" height="9" fill="none" viewBox="0 0 24 24" className={`transition-transform ${expanded ? 'rotate-180' : ''}`}>
                  <path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </button>
            )}
          </div>

          {single && (
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <button onClick={e => { e.stopPropagation(); onVehicleSelect(single.vin) }}
                  className="font-mono text-[11px] font-bold text-blue-600 hover:underline flex-shrink-0">
                  {single.vehicle?.stock_number ? `#${single.vehicle.stock_number}` : single.vin.slice(-8)}
                </button>
                {single.vehicle && (
                  <span className="text-[12px] text-slate-600 truncate">
                    {single.vehicle.display_name}
                  </span>
                )}
                <span className="text-[11px] text-slate-400">{single.assigned_employee_id ?? 'Unassigned'}</span>
              </div>
              <button onClick={() => onSelectTask(single.task_id)}
                className="flex-shrink-0 text-[12px] font-bold px-3.5 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-all">
                View
              </button>
            </div>
          )}

          {isMulti && !expanded && (
            <div className="text-[11px] text-slate-400">
              {(() => {
                // Demo Polish: department is null for every task today,
                // so counting distinct values (including the "Unassigned"
                // placeholder) always produced the false claim "across 1
                // department(s)". Only state a department count when at
                // least one task actually has one.
                const departments = new Set(group.tasks.map(t => t.department).filter((d): d is string => d !== null))
                return departments.size > 0
                  ? `${group.tasks.length} vehicles across ${departments.size} department${departments.size === 1 ? '' : 's'}`
                  : `${group.tasks.length} vehicles`
              })()}
            </div>
          )}
        </div>
      </div>

      {expanded && isMulti && (
        <div className="px-4 pb-3 ml-1 divide-y divide-slate-50">
          {group.tasks.map(t => {
            const ds = deriveDisplayStatus(t)
            return (
              <div key={t.task_id} className="flex items-center gap-3 py-1.5">
                <button onClick={e => { e.stopPropagation(); onVehicleSelect(t.vin) }}
                  className="font-mono text-[11px] font-bold text-blue-600 hover:underline flex-shrink-0">
                  {t.vehicle?.stock_number ? `#${t.vehicle.stock_number}` : t.vin.slice(-8)}
                </button>
                <span className="text-[12px] text-slate-700 flex-1 truncate">
                  {t.vehicle ? (t.vehicle.display_name ?? t.vin) : t.vin}
                </span>
                <span className={`text-[11px] flex-shrink-0 ${toneClasses[ds.tone]}`}>{ds.label}</span>
                <button onClick={() => onSelectTask(t.task_id)}
                  className="flex-shrink-0 text-[10px] font-bold text-slate-500 hover:text-blue-600 px-2 py-0.5 rounded border border-slate-200 hover:border-blue-300 transition-colors">
                  View
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Task Detail ──────────────────────────────────────────────────────────────

function TaskDetail({ task, onBack, onVehicleSelect }: {
  task: TaskDTO; onBack: () => void; onVehicleSelect: (vin: string) => void
}) {
  const ds = deriveDisplayStatus(task)
  const pb = task.priority ? priorityBadge[task.priority] : null
  const canStart = task.commitment_standing === 'outstanding' && task.execution_status === 'not_started'
  const canPauseOrComplete = task.commitment_standing === 'outstanding' && task.execution_status === 'in_progress'

  return (
    <div className="flex-1 flex flex-col overflow-hidden min-h-0">
      <div className="flex-shrink-0 bg-white border-b border-slate-200 px-5 py-3">
        <div className="flex items-center gap-2 mb-2.5">
          <button onClick={onBack} className="flex items-center gap-1.5 text-[12px] font-semibold text-slate-400 hover:text-slate-700 transition-colors group">
            <svg width="13" height="13" fill="none" viewBox="0 0 24 24" className="group-hover:-translate-x-0.5 transition-transform">
              <path d="m15 18-6-6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            Tasks
          </button>
          <span className="text-slate-200">/</span>
          <span className="text-[12px] font-medium text-slate-600">{humanize(task.task_type)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <h1 className="text-[18px] font-bold text-slate-900">{humanize(task.task_type)}</h1>
            {pb && task.priority && (
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase tracking-wide ${pb.badge}`}>{task.priority}</span>
            )}
            <span className={`text-[11px] ${toneClasses[ds.tone]}`}>{ds.label}</span>
          </div>
          <div className="flex items-center gap-2">
            {canStart && (
              <button disabled title="Coming soon -- write APIs are out of this sprint's scope"
                className="text-[12px] font-bold px-4 py-1.5 bg-blue-300 text-white rounded-lg cursor-not-allowed">Start Task</button>
            )}
            {canPauseOrComplete && <>
              <button disabled title="Coming soon" className="text-[12px] font-semibold px-3 py-1.5 bg-white text-slate-300 border border-slate-200 rounded-lg cursor-not-allowed">Pause</button>
              <button disabled title="Coming soon -- write APIs are out of this sprint's scope" className="text-[12px] font-bold px-4 py-1.5 bg-emerald-300 text-white rounded-lg cursor-not-allowed">Mark Complete</button>
            </>}
            <button disabled title="Coming soon" className="text-[12px] text-slate-300 px-2 py-1.5 cursor-not-allowed">Cancel</button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
        <div className="flex gap-5 p-5">
          <div className="flex-1 space-y-4 min-w-0">
            <p className="text-[13px] text-slate-600 leading-relaxed">{task.reason ?? 'No reason recorded.'}</p>

            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-100">
                <span className="text-[12px] font-bold text-slate-700">History</span>
              </div>
              <div className="px-5 py-4">
                <div className="relative pl-5 space-y-3.5">
                  <div className="absolute left-1.5 top-1 bottom-1 w-px bg-slate-100" />
                  <div className="relative flex items-start gap-3">
                    <div className="absolute -left-4 top-1 w-2.5 h-2.5 rounded-full border-2 border-white bg-blue-400" />
                    <div>
                      <div className="text-[12px] font-medium text-slate-800">Created</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">{formatDateTime(task.created_at)}</div>
                    </div>
                  </div>
                  {task.completed_at && (
                    <div className="relative flex items-start gap-3">
                      <div className="absolute -left-4 top-1 w-2.5 h-2.5 rounded-full border-2 border-white bg-emerald-400" />
                      <div>
                        <div className="text-[12px] font-medium text-slate-800">Discharged — {ds.label}</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">{formatDateTime(task.completed_at)}</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="flex-shrink-0 space-y-3" style={{ width: '252px' }}>
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-100">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Vehicle</span>
              </div>
              <button onClick={() => onVehicleSelect(task.vin)} className="w-full px-4 py-3 text-left hover:bg-slate-50 transition-colors group">
                <span className="font-mono text-[11px] font-bold text-blue-600 group-hover:underline block">
                  {task.vehicle?.stock_number ? `#${task.vehicle.stock_number}` : task.vin.slice(-8)}
                </span>
                {task.vehicle && (
                  <div className="text-[12px] font-semibold text-slate-800 mt-0.5">
                    {task.vehicle.display_name}
                  </div>
                )}
              </button>
            </div>

            {ds.label === 'Waiting Verification' && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <div className="text-[12px] font-bold text-amber-800 mb-1">Waiting for Inventory Sync</div>
                <p className="text-[11px] text-amber-700 leading-relaxed">
                  Execution was marked complete, but the commitment itself is still outstanding until the next
                  sync confirms it. This is a real, surfaced disagreement, not an error.
                </p>
              </div>
            )}

            <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-2 text-[12px]">
              <div className="flex justify-between">
                <span className="text-slate-400">Assigned</span>
                <span className="font-medium text-slate-700">{task.assigned_employee_id ?? 'Unassigned'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Department</span>
                <span className="font-medium text-slate-700">{task.department ?? '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Commitment</span>
                <span className="font-medium text-slate-700 capitalize">{task.commitment_standing}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Execution</span>
                <span className="font-medium text-slate-700 capitalize">{task.execution_status.replace('_', ' ')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Ratification</span>
                <span className="font-medium text-slate-700">{ratificationLabel(task)}</span>
              </div>
              {task.ratified_by && (
                <div className="flex justify-between">
                  <span className="text-slate-400">Ratified by</span>
                  <span className="font-medium text-slate-700">{task.ratified_by}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Loading / error states ────────────────────────────────────────────────────

const spinner = (
  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" className="animate-spin">
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.2" />
    <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
  </svg>
)

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function Tasks({ onVehicleSelect }: { onVehicleSelect: (s: string) => void }) {
  const state = useApi(() => getTasks(), [])
  const [filter, setFilter] = useState<SidebarFilter>({ type: 'queue', value: 'all' })
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const tasks = state.status === 'success' ? state.data : []
  const selectedTask = tasks.find(t => t.task_id === selectedId) ?? null

  const visible = useMemo(() => tasks.filter(t => matchesFilter(t, filter)), [tasks, filter])

  const groups = useMemo<TaskTypeGroup[]>(() => {
    const byType = new Map<string, TaskDTO[]>()
    for (const t of visible) {
      const list = byType.get(t.task_type) ?? []
      list.push(t)
      byType.set(t.task_type, list)
    }
    return Array.from(byType.entries()).map(([taskType, ts]) => ({ taskType, tasks: ts }))
  }, [visible])

  const outstanding = visible.filter(t => t.commitment_standing === 'outstanding' && t.execution_status === 'not_started').length
  const inProgress = visible.filter(t => t.commitment_standing === 'outstanding' && t.execution_status === 'in_progress').length

  if (selectedTask) {
    return (
      <div className="flex-1 flex overflow-hidden min-h-0">
        <Sidebar tasks={tasks} filter={filter} onFilter={setFilter} />
        <TaskDetail task={selectedTask} onBack={() => setSelectedId(null)} onVehicleSelect={onVehicleSelect} />
      </div>
    )
  }

  return (
    <div className="flex-1 flex overflow-hidden min-h-0">
      <Sidebar tasks={tasks} filter={filter} onFilter={setFilter} />

      <div className="flex-1 flex flex-col overflow-hidden min-h-0">
        <div className="flex-shrink-0 flex items-center justify-between px-5 py-2.5 bg-white border-b border-slate-200">
          <div className="flex items-center gap-3">
            <h2 className="text-[14px] font-bold text-slate-900">Dispatch Queue</h2>
            {outstanding > 0 && <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">{outstanding} outstanding</span>}
            {inProgress  > 0 && <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">{inProgress} in progress</span>}
          </div>
          {state.status === 'success' && <span className="text-[11px] text-slate-400">{visible.length} tasks</span>}
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-3 space-y-2" style={{ scrollbarWidth: 'thin' }}>
          {state.status === 'loading' && (
            <div className="flex flex-col items-center justify-center h-48 text-slate-400 gap-3">
              {spinner}
              <p className="text-[13px] font-medium">Loading tasks…</p>
            </div>
          )}

          {state.status === 'error' && (
            <div className="flex flex-col items-center justify-center h-48 text-center gap-2">
              <p className="text-[13px] font-medium text-red-500">
                {isBackendUnavailable(state.error) ? 'The LotSync API is unreachable.' : 'Something went wrong loading tasks.'}
              </p>
              <p className="text-[11px] text-slate-400">{state.error.message}</p>
            </div>
          )}

          {state.status === 'success' && groups.length === 0 && (
            <div className="flex flex-col items-center justify-center h-48 text-slate-400">
              <svg width="28" height="28" fill="none" viewBox="0 0 24 24" className="mb-2 opacity-30">
                <path d="M9 11l3 3L22 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              <p className="text-[13px] font-medium">No tasks in this queue</p>
            </div>
          )}

          {state.status === 'success' && groups.map(group => (
            <GroupCard key={group.taskType} group={group} onSelectTask={setSelectedId} onVehicleSelect={onVehicleSelect} />
          ))}
        </div>
      </div>
    </div>
  )
}
