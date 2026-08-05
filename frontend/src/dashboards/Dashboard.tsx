// Dashboard.tsx — unified "what should I work on today" home screen
//
// Sprint 3.8 alignment introduced this screen as a single home page for
// every role, replacing the five role-specific dashboards, but left it
// on mock data. Friday Demo Build: wired to real data.
//
// No backend changes were needed -- GET /dashboard (connected_systems,
// inventory_health, recent_activity), GET /tasks, and GET /recommendations
// already expose everything this screen needs; "Generated RecovR tasks"
// and "Generated MDD tasks" are simply outstanding Tasks filtered by
// task_type ('install_recovr_device' / 'install_mdd_beacon') client-side,
// the same real per-source fields Tasks.tsx and VehiclesList.tsx already
// read directly rather than inventing a backend concept that doesn't exist.
//
// Same "render real gaps honestly" rule as every other Sprint 3 screen:
// no scheduled-next-sync time is shown (nothing schedules syncs), and an
// empty Recommendations/Tasks list renders as an empty state, not
// mock rows.

import { useMemo } from 'react'
import { getDashboard } from '../api/dashboard'
import { getTasks } from '../api/tasks'
import { getRecommendations } from '../api/recommendations'
import { useApi } from '../api/useApi'
import { isBackendUnavailable } from '../api/client'
import type { TaskDTO, RecommendationDTO } from '../api/types'

type AppRole =
  | 'Lot Staff'
  | 'Lot Manager'
  | 'Tower Manager'
  | 'Controller'
  | 'Sales Manager'
  | 'Recon Manager'
  | 'Service Advisor'
  | 'Detail Team'

const roleMeta: Record<AppRole, { name: string; greeting: string }> = {
  'Lot Staff':       { name: 'Marcus',  greeting: 'Here\'s your work queue for today.' },
  'Lot Manager':     { name: 'Jordan',  greeting: 'Here\'s an overview of today\'s operations.' },
  'Tower Manager':   { name: 'Rosa',    greeting: 'Here\'s the operational summary for today.' },
  'Controller':      { name: 'Sarah',   greeting: 'Here\'s the inventory status for today.' },
  'Sales Manager':   { name: 'Ben',     greeting: 'Here\'s today\'s vehicle and task summary.' },
  'Recon Manager':   { name: 'Alex',    greeting: 'Here\'s today\'s recon pipeline.' },
  'Service Advisor': { name: 'Lisa',    greeting: 'Here\'s your service-related vehicle activity.' },
  'Detail Team':     { name: 'Team',    greeting: 'Here\'s today\'s detail assignments.' },
}

// Same PRIORITY_RANK / priorityBadge palette as Tasks.tsx -- kept in
// sync deliberately so a task looks the same wherever it appears.
const PRIORITY_RANK: Record<string, number> = { Critical: 0, High: 1, Medium: 2, Low: 3 }
const priorityBadge: Record<string, { bar: string; text: string }> = {
  Critical: { bar: 'bg-red-500',    text: 'text-red-700' },
  High:     { bar: 'bg-orange-400', text: 'text-orange-700' },
  Medium:   { bar: 'bg-amber-400',  text: 'text-amber-700' },
  Low:      { bar: 'bg-slate-300',  text: 'text-slate-500' },
}

const severityBadge: Record<string, string> = {
  Critical: 'bg-red-50 text-red-700 border border-red-200',
  High: 'bg-orange-50 text-orange-700 border border-orange-200',
  Medium: 'bg-amber-50 text-amber-700 border border-amber-200',
  Low: 'bg-slate-100 text-slate-600 border border-slate-200',
}

// Same brand-name issue as sourceLabel() above, applied to task_type
// (e.g. "install_recovr_device" -> "Install RecovR Device", not
// "Install Recovr Device"). Tasks.tsx's own humanize() got the same fix.
function humanize(taskType: string): string {
  const words = taskType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  return words.replace(/\bRecovr\b/, 'RecovR').replace(/\bMdd\b/, 'MDD')
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

function todayLabel(): string {
  return new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
}

// Source keys are stored lowercase (sync_run.source); these are real
// product/brand names, not generic words, so `capitalize` CSS mangles
// three of the five ("Mdd", "Recovr", "Rapidrecon"). Same fix applied to
// InventorySync.tsx and VehicleDetail.tsx's system cards, which had the
// identical raw-source-key + `capitalize` pattern.
const SOURCE_LABEL: Record<string, string> = {
  tekion: 'Tekion', keyper: 'Keyper', mdd: 'MDD', recovr: 'RecovR', rapidrecon: 'RapidRecon',
}
function sourceLabel(source: string): string {
  return SOURCE_LABEL[source] ?? source
}

function ChevronRight() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-slate-300 flex-shrink-0">
      <path d="M5 3l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function CheckCircle({ className }: { className?: string }) {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className={className}>
      <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M4.5 7l2 2 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function WarnIcon({ className }: { className?: string }) {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className={className}>
      <path d="M7 1.5L13 12.5H1L7 1.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
      <path d="M7 6v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <circle cx="7" cy="10.5" r="0.5" fill="currentColor"/>
    </svg>
  )
}

export default function Dashboard({ role, onVehicleSelect, onNavigate }: {
  role: AppRole
  onVehicleSelect: (vin: string) => void
  onNavigate: (tab: 'tasks' | 'inventory-sync') => void
}) {
  const meta = roleMeta[role]

  const dashboardState = useApi(() => getDashboard(), [])
  const tasksState = useApi(() => getTasks({ commitment_standing: 'outstanding' }), [])
  const recsState = useApi(() => getRecommendations({ status: 'open' }), [])

  const connectedSystems = dashboardState.status === 'success' ? dashboardState.data.connected_systems : {}
  const inventoryHealth = dashboardState.status === 'success' ? dashboardState.data.inventory_health : null
  const recentActivity = dashboardState.status === 'success' ? dashboardState.data.recent_activity : []
  const tasks: TaskDTO[] = tasksState.status === 'success' ? tasksState.data : []
  const recommendations: RecommendationDTO[] = recsState.status === 'success' ? recsState.data : []

  const sortedTasks = useMemo(
    () =>
      [...tasks].sort((a, b) => {
        const pr = (PRIORITY_RANK[a.priority ?? ''] ?? 99) - (PRIORITY_RANK[b.priority ?? ''] ?? 99)
        return pr !== 0 ? pr : b.task_id - a.task_id
      }),
    [tasks],
  )

  const recovrCount = tasks.filter(t => t.task_type === 'install_recovr_device').length
  const mddCount = tasks.filter(t => t.task_type === 'install_mdd_beacon').length

  const systemEntries = Object.entries(connectedSystems)
  const hasSyncIssue = systemEntries.some(([, s]) => s.status !== 'complete')
  const lastSyncAt = systemEntries.reduce<string | null>((latest, [, s]) => {
    const candidate = s.completed_at ?? s.started_at
    if (!candidate) return latest
    if (!latest || new Date(candidate) > new Date(latest)) return candidate
    return latest
  }, null)

  return (
    <div className="h-full flex flex-col bg-slate-50 overflow-hidden">
      {/* Header */}
      <div className="bg-white border-b border-slate-100 px-6 py-4 flex-shrink-0 flex items-center justify-between">
        <div>
          <div className="text-[20px] font-bold text-slate-900 leading-tight">
            Good morning, {meta.name}.
          </div>
          <div className="text-[13px] text-slate-500 mt-0.5">{meta.greeting}</div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-[12px] text-slate-400 font-medium">{todayLabel()}</div>
          {systemEntries.length === 0 ? null : hasSyncIssue ? (
            <span className="inline-flex items-center gap-1.5 bg-amber-50 border border-amber-200 text-amber-700 text-[11px] font-semibold px-2.5 py-1 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block"></span>
              Sync Attention Needed
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 bg-emerald-50 border border-emerald-200 text-emerald-700 text-[11px] font-semibold px-2.5 py-1 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block"></span>
              Systems Healthy
            </span>
          )}
        </div>
      </div>

      {/* Stat strip -- real reconciliation output, not typed-in numbers */}
      <div className="grid grid-cols-4 gap-4 px-6 pt-5 flex-shrink-0">
        {[
          { label: 'RecovR Installs Pending', value: tasksState.status === 'success' ? recovrCount : '—', color: 'text-blue-600' },
          { label: 'MDD Installs Pending', value: tasksState.status === 'success' ? mddCount : '—', color: 'text-blue-600' },
          { label: 'Open Recommendations', value: recsState.status === 'success' ? recommendations.length : '—', color: 'text-violet-600' },
          { label: 'Inventory Health', value: inventoryHealth?.health_percentage != null ? `${inventoryHealth.health_percentage}%` : '—', color: 'text-emerald-600' },
        ].map(stat => (
          <div key={stat.label} className="bg-white rounded-2xl border border-slate-100 px-4 py-3">
            <p className="text-[11px] text-slate-500 mb-1">{stat.label}</p>
            <p className={`text-[22px] font-bold leading-none ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Body */}
      <div className="flex-1 flex gap-5 px-6 py-5 overflow-hidden min-h-0">
        {/* Left column */}
        <div className="flex-1 overflow-y-auto space-y-5 min-w-0 pr-1">
          {/* Open Tasks */}
          <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-50">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-semibold text-slate-900">Open Tasks</span>
                <span className="bg-slate-100 text-slate-500 text-[11px] font-semibold px-2 py-0.5 rounded-full">
                  {tasksState.status === 'success' ? tasks.length : '…'}
                </span>
              </div>
              <button
                onClick={() => onNavigate('tasks')}
                className="text-[12px] text-blue-600 font-medium hover:text-blue-700 transition-colors"
              >
                View All
              </button>
            </div>

            {tasksState.status === 'error' && (
              <div className="px-4 py-8 text-center text-[13px] text-slate-400">
                {isBackendUnavailable(tasksState.error) ? 'The LotSync API is unreachable.' : 'Could not load tasks.'}
              </div>
            )}
            {tasksState.status === 'loading' && (
              <div className="px-4 py-8 text-center text-[13px] text-slate-400">Loading tasks…</div>
            )}
            {tasksState.status === 'success' && tasks.length === 0 && (
              <div className="px-4 py-8 text-center text-[13px] text-slate-400">No outstanding tasks.</div>
            )}

            <div>
              {sortedTasks.slice(0, 8).map((task) => {
                const p = priorityBadge[task.priority ?? ''] ?? priorityBadge.Low
                return (
                  <div
                    key={task.task_id}
                    className="relative flex items-center gap-3 px-4 py-3 border-b border-slate-50 last:border-0 hover:bg-slate-50/60 cursor-pointer transition-colors"
                    onClick={() => onVehicleSelect(task.vin)}
                  >
                    <div className={`absolute left-0 top-0 bottom-0 w-[3px] ${p.bar}`} />
                    <div className={`w-2 h-2 rounded-full flex-shrink-0 ${p.bar} ml-1`} />

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[13px] font-semibold text-slate-900 leading-snug">{humanize(task.task_type)}</span>
                        <span className="text-[10px] font-mono text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded font-medium">
                          {task.vehicle?.stock_number ?? task.vin}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                        {/* Demo Polish: don't claim "Vehicle details unavailable" when
                            the reason line right next to it already names the vehicle
                            (e.g. "...(2024 Chevrolet Colorado)") -- just omit this line
                            when there's genuinely nothing else on file. */}
                        {task.vehicle?.display_name && (
                          <span className="text-[11px] text-slate-400">{task.vehicle.display_name}</span>
                        )}
                        {task.reason && <span className="text-[10px] text-slate-400">{task.reason}</span>}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      {/* Demo Polish: priority is unset for most tasks today (no rule
                          assigns it yet) -- showing "Low" implied a real classification
                          that never happened. Omit the label rather than fabricate one. */}
                      {task.priority && <span className={`text-[10px] font-semibold ${p.text}`}>{task.priority}</span>}
                      <ChevronRight />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Recommendations */}
          <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-50">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-semibold text-slate-900">Recommendations</span>
                <span className="bg-slate-100 text-slate-500 text-[11px] font-semibold px-2 py-0.5 rounded-full">
                  {recsState.status === 'success' ? recommendations.length : '…'}
                </span>
              </div>
            </div>

            {recsState.status === 'error' && (
              <div className="px-4 py-8 text-center text-[13px] text-slate-400">
                {isBackendUnavailable(recsState.error) ? 'The LotSync API is unreachable.' : 'Could not load recommendations.'}
              </div>
            )}
            {recsState.status === 'loading' && (
              <div className="px-4 py-8 text-center text-[13px] text-slate-400">Loading recommendations…</div>
            )}
            {recsState.status === 'success' && recommendations.length === 0 && (
              <div className="px-4 py-8 text-center text-[13px] text-slate-400">No open recommendations.</div>
            )}

            <div>
              {recommendations.slice(0, 6).map((rec) => (
                <div
                  key={rec.recommendation_id}
                  className="relative flex items-center gap-3 px-4 py-3 border-b border-slate-50 last:border-0 hover:bg-slate-50/60 cursor-pointer transition-colors"
                  onClick={() => onVehicleSelect(rec.vin)}
                >
                  <div className="flex-1 min-w-0 ml-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[10px] font-mono text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded font-medium">
                        {rec.vehicle?.stock_number ?? rec.vin}
                      </span>
                      <span className="text-[13px] font-semibold text-slate-900">
                        {rec.vehicle?.display_name ?? 'Vehicle'}
                      </span>
                      {rec.severity && (
                        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${severityBadge[rec.severity] ?? severityBadge.Low}`}>
                          {rec.severity}
                        </span>
                      )}
                    </div>
                    <div className="mt-0.5 text-[11px] text-slate-500">{rec.title ?? rec.detail ?? 'No detail available'}</div>
                  </div>
                  <ChevronRight />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right column */}
        <div className="w-72 flex-shrink-0 overflow-y-auto space-y-4 min-h-0">
          {/* Recent Activity */}
          <div className="bg-white rounded-2xl border border-slate-100 p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[13px] font-semibold text-slate-900">Recent Activity</span>
            </div>

            {dashboardState.status === 'error' && (
              <p className="text-[12px] text-slate-400">
                {isBackendUnavailable(dashboardState.error) ? 'The LotSync API is unreachable.' : 'Could not load activity.'}
              </p>
            )}
            {dashboardState.status === 'loading' && <p className="text-[12px] text-slate-400">Loading…</p>}
            {dashboardState.status === 'success' && recentActivity.length === 0 && (
              <p className="text-[12px] text-slate-400">No activity recorded yet.</p>
            )}

            <div>
              {recentActivity.slice(0, 8).map((entry) => (
                <div key={entry.event_id} className="flex items-start gap-2.5 py-1.5">
                  <div className="flex-shrink-0 mt-[5px]">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-[10px] font-mono text-slate-400">{formatTimestamp(entry.event_time ?? entry.observed_at)}</span>
                      {entry.vehicle?.stock_number && (
                        <span className="text-[10px] font-mono text-blue-500 bg-blue-50 px-1 rounded">
                          {entry.vehicle.stock_number}
                        </span>
                      )}
                    </div>
                    <div className="text-[12px] text-slate-700 leading-snug mt-0.5">{entry.summary ?? entry.event_type}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Sync Health */}
          <div className="bg-white rounded-2xl border border-slate-100 p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[13px] font-semibold text-slate-900">Inventory Sync</span>
              {systemEntries.length > 0 && (
                hasSyncIssue ? (
                  <span className="text-[10px] font-semibold text-amber-600 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded-full">
                    Attention
                  </span>
                ) : (
                  <span className="text-[10px] font-semibold text-emerald-600 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded-full">
                    Healthy
                  </span>
                )
              )}
            </div>

            {dashboardState.status === 'loading' && <p className="text-[12px] text-slate-400">Loading…</p>}
            {dashboardState.status === 'success' && systemEntries.length === 0 && (
              <p className="text-[12px] text-slate-400">No syncs recorded yet — upload reports to get started.</p>
            )}

            {lastSyncAt && (
              <div className="text-[12px] text-slate-700 font-medium">Last sync: {formatTimestamp(lastSyncAt)}</div>
            )}

            {inventoryHealth && inventoryHealth.total_vehicles > 0 && (
              <div className="mt-3 flex items-center gap-3 bg-slate-50 rounded-xl px-3 py-2.5">
                <div className="text-center flex-1">
                  <div className="text-[16px] font-bold text-slate-900">{inventoryHealth.total_vehicles.toLocaleString()}</div>
                  <div className="text-[10px] text-slate-400">vehicles tracked</div>
                </div>
                <div className="w-px h-8 bg-slate-200" />
                <div className="text-center flex-1">
                  <div className="text-[16px] font-bold text-emerald-600">{inventoryHealth.healthy_vehicles.toLocaleString()}</div>
                  <div className="text-[10px] text-slate-400">no open tasks</div>
                </div>
              </div>
            )}

            {systemEntries.length > 0 && (
              <div className="mt-3 space-y-2.5">
                {systemEntries.map(([source, sys]) => (
                  <div key={source} className="flex items-start justify-between">
                    <span className="text-[12px] text-slate-600">{sourceLabel(source)}</span>
                    {sys.status === 'complete' ? (
                      <div className="flex items-center gap-1">
                        <CheckCircle className="text-emerald-500" />
                        <span className="text-[11px] text-emerald-600 font-medium">OK</span>
                      </div>
                    ) : (
                      <div className="flex items-start gap-1">
                        <WarnIcon className="text-amber-500 mt-0.5 flex-shrink-0" />
                        <div className="text-right">
                          <div className="text-[11px] text-amber-600 font-semibold leading-tight capitalize">{sys.status.replace(/_/g, ' ')}</div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="mt-4 pt-3 border-t border-slate-50">
              <button
                onClick={() => onNavigate('inventory-sync')}
                className="text-[11px] text-blue-600 font-medium hover:text-blue-700 transition-colors flex items-center gap-1"
              >
                View Inventory Sync
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M2.5 6h7M6.5 3l3 3-3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
