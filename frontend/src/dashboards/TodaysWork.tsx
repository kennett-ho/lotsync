/**
 * Sprint 12 (Rail C) -- Today's Work: the Lot Staff landing surface.
 *
 * An execution-first COMPOSITION over the exact same data the rest of
 * the app uses -- GET /tasks (outstanding), GET /dashboard's
 * connected_systems for evidence freshness, and the existing
 * work-order PDF endpoint. No new backend semantics, no second task
 * model: grouping, priorities, describeTask wording, and the
 * commitment/execution vocabulary are all shared with Tasks.tsx and
 * Dashboard.tsx (Rail C rule: emphasis changes, truth doesn't).
 *
 * Differences from the manager Overview are deliberate:
 * - groups render EXPANDED by default -- a lot-staff user came here
 *   to do the work, not to survey categories;
 * - each vehicle row leads straight into Vehicle Detail (the "why"
 *   evidence);
 * - the printable work order is a first-class header action;
 * - manager judgment panels (health %, recommendations review) are
 *   absent -- that analysis lives on Overview for the roles that do
 *   it. The evidence lot staff DO need (how fresh is this?) is the
 *   freshness line below the title.
 */

import { useEffect, useMemo, useState } from 'react'
import { getTasks, getWorkOrderPdf } from '../api/tasks'
import { useApi } from '../api/useApi'
import { useDashboardData } from '../api/dashboardData'
import { isBackendUnavailable } from '../api/client'
import type { TaskDTO } from '../api/types'
import { describeTask, describeTaskDetail } from '../taskDisplay'
import { track } from '../observability/analytics'

const PRIORITY_RANK: Record<string, number> = { Critical: 0, High: 1, Medium: 2, Low: 3 }
const priorityBadge: Record<string, { bar: string; text: string }> = {
  Critical: { bar: 'bg-red-500',    text: 'text-red-700' },
  High:     { bar: 'bg-orange-400', text: 'text-orange-700' },
  Medium:   { bar: 'bg-amber-400',  text: 'text-amber-700' },
  Low:      { bar: 'bg-slate-300',  text: 'text-slate-500' },
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

function todayLabel(): string {
  return new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })
}

interface WorkGroup { taskType: string; tasks: TaskDTO[] }

const spinner = (
  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" className="animate-spin">
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.2" />
    <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
  </svg>
)

const printerIcon = (
  <svg width="14" height="14" fill="none" viewBox="0 0 24 24">
    <path d="M6 9V3h12v6M6 18H4a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1h16a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-2M6 14h12v7H6z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

/** Triggers a browser download for the PDF a work-order fetch resolved to. */
function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export default function TodaysWork({ onVehicleSelect }: { onVehicleSelect: (vin: string) => void }) {
  const tasksState = useApi(() => getTasks({ commitment_standing: 'outstanding' }), [])
  // Sprint 14 (Rail J): shared per-view /dashboard fetch (freshness
  // metadata only) -- see api/dashboardData.tsx.
  const dashboardState = useDashboardData(true).state
  const [workOrderStatus, setWorkOrderStatus] = useState<'idle' | 'generating' | 'error'>('idle')

  // Sprint 12 analytics: does Lot Staff actually use the role-focused
  // work surface as their operational starting point? Once per mount.
  useEffect(() => { track('today_work_opened') }, [])

  const tasks: TaskDTO[] = tasksState.status === 'success' ? tasksState.data : []

  const groups = useMemo<WorkGroup[]>(() => {
    const sorted = [...tasks].sort((a, b) => {
      const pr = (PRIORITY_RANK[a.priority ?? ''] ?? 99) - (PRIORITY_RANK[b.priority ?? ''] ?? 99)
      return pr !== 0 ? pr : b.task_id - a.task_id
    })
    const order: string[] = []
    const byType = new Map<string, TaskDTO[]>()
    for (const t of sorted) {
      if (!byType.has(t.task_type)) { byType.set(t.task_type, []); order.push(t.task_type) }
      byType.get(t.task_type)!.push(t)
    }
    return order.map(taskType => ({ taskType, tasks: byType.get(taskType)! }))
  }, [tasks])

  // Evidence freshness (S12-13): the latest completed sync per the
  // same connected_systems data every other surface reads. Display
  // only -- per-source Fresh/Aging/Stale classification is Sprint 17.
  const systemEntries = dashboardState.status === 'success'
    ? Object.entries(dashboardState.data.connected_systems) : []
  const lastSyncAt = systemEntries.reduce<string | null>((latest, [, s]) => {
    const candidate = s.completed_at ?? s.started_at
    if (!candidate) return latest
    if (!latest || new Date(candidate) > new Date(latest)) return candidate
    return latest
  }, null)

  const handleGenerateWorkOrder = async () => {
    setWorkOrderStatus('generating')
    try {
      const { blob, filename } = await getWorkOrderPdf()
      downloadBlob(blob, filename)
      setWorkOrderStatus('idle')
      track('work_order_generated')
    } catch {
      setWorkOrderStatus('error')
    }
  }

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-3 mb-1">
          <div>
            <h1 className="text-[20px] font-bold text-slate-900 leading-tight">Today&rsquo;s Work</h1>
            <p className="text-[13px] text-slate-500 mt-0.5">{todayLabel()}</p>
          </div>
          <div className="flex items-center gap-3">
            {workOrderStatus === 'error' && (
              <span role="alert" className="text-[11px] text-red-600">Couldn&rsquo;t generate the work order.</span>
            )}
            <button
              onClick={handleGenerateWorkOrder}
              disabled={workOrderStatus === 'generating'}
              className="flex items-center gap-1.5 bg-white hover:bg-slate-50 disabled:text-slate-400 border border-slate-200 text-slate-700 text-[12px] font-semibold px-3.5 py-2 rounded-lg transition-colors">
              {workOrderStatus === 'generating' ? spinner : printerIcon}
              {workOrderStatus === 'generating' ? 'Generating…' : 'Generate Work Order'}
            </button>
          </div>
        </div>

        {/* Evidence freshness -- when the systems last reported. */}
        {lastSyncAt && (
          <p className="text-[12px] text-slate-500 mb-5">
            Based on evidence from the last sync: <span className="font-semibold text-slate-600">{formatTimestamp(lastSyncAt)}</span>
          </p>
        )}
        {!lastSyncAt && <div className="mb-5" />}

        {tasksState.status === 'loading' && (
          <div role="status" className="flex flex-col items-center justify-center h-48 text-slate-500 gap-3">
            {spinner}
            <p className="text-[13px] font-medium">Loading today&rsquo;s work…</p>
          </div>
        )}

        {tasksState.status === 'error' && (
          <div role="alert" className="bg-white rounded-2xl border border-slate-100 px-5 py-10 text-center text-[13px] text-slate-500">
            {isBackendUnavailable(tasksState.error) ? 'The API is unreachable right now.' : 'Could not load today’s work.'}
          </div>
        )}

        {tasksState.status === 'success' && tasks.length === 0 && (
          <div className="bg-white rounded-2xl border border-slate-100 px-5 py-12 text-center">
            <p className="text-[15px] font-semibold text-slate-700">No outstanding work</p>
            <p className="text-[13px] text-slate-500 mt-1.5 max-w-sm mx-auto">
              You&rsquo;re all caught up. New work appears here when the next
              inventory sync finds something that needs doing.
            </p>
          </div>
        )}

        {/* Work groups -- expanded by default: this surface exists to DO
            the work, not to survey it. */}
        <div className="space-y-4">
          {groups.map(group => {
            const display = describeTask(group.tasks[0])
            const topPriority = group.tasks
              .map(t => t.priority)
              .filter((p): p is string => p !== null)
              .sort((a, b) => (PRIORITY_RANK[a] ?? 99) - (PRIORITY_RANK[b] ?? 99))[0]
            const pb = priorityBadge[topPriority ?? ''] ?? priorityBadge.Low
            return (
              <div key={group.taskType} className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
                <div className="relative px-5 py-3.5 border-b border-slate-50">
                  <div className={`absolute left-0 top-0 bottom-0 w-[3px] ${pb.bar}`} />
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[14px] font-bold text-slate-900">{display.groupTitle}</span>
                    <span className="flex-shrink-0 text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                      {group.tasks.length} vehicle{group.tasks.length === 1 ? '' : 's'}
                    </span>
                  </div>
                  {/* The why -- same shared describeTask wording as every
                      other surface. */}
                  <p className="text-[12px] text-slate-500 mt-0.5 leading-snug">{display.description}</p>
                </div>
                <div className="divide-y divide-slate-50">
                  {group.tasks.map(task => {
                    const tp = priorityBadge[task.priority ?? ''] ?? priorityBadge.Low
                    const detail = describeTaskDetail(task)
                    return (
                      <button key={task.task_id} onClick={() => onVehicleSelect(task.vin)}
                        className="w-full text-left flex items-center justify-between gap-3 px-5 py-3.5 hover:bg-slate-50/70 transition-colors">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[10px] font-mono text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded font-medium">
                              {task.vehicle?.stock_number ?? task.vin}
                            </span>
                            <span className="text-[13px] font-semibold text-slate-900">{task.vehicle?.display_name ?? 'Vehicle'}</span>
                            {task.priority && <span className={`text-[10px] font-semibold ${tp.text}`}>{task.priority}</span>}
                          </div>
                          {detail && <p className="text-[11px] text-slate-500 mt-0.5">{detail}</p>}
                        </div>
                        <span className="flex-shrink-0 flex items-center gap-1 text-[11px] font-semibold text-blue-600">
                          Open Vehicle
                          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M5 3l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                        </span>
                      </button>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
