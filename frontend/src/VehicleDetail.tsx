// VehicleDetail.tsx — single-vehicle operational source of truth
//
// Sprint 3 (Frontend Integration): wired to GET /vehicles/{vin}
// (api/routers/vehicles.py's get_vehicle_detail, VehicleDetailDTO per
// API_CONTRACTS.md). This file does no business-logic interpretation
// of its own -- every status/severity/tone shown is a direct read of a
// backend field, mapped only to a display color, never re-derived.
//
// Known, already-documented gaps this screen renders honestly rather
// than papering over with invented data (see PHASE_3_SPRINT_3_REVIEW.md):
// vehicle photo (API_CONTRACTS.md Section 9 already names this as
// unsourced), lot zone / physical location, and "days in inventory" --
// none of these exist anywhere in DATA_MODEL.md's Vehicle shape, so
// none are computed client-side. Rather than remove those panels
// outright (this sprint's UI is frozen), they render an honest
// "Not tracked yet" note in place of a fabricated value.

import { useMemo, useState } from 'react'
import { getVehicleDetail } from './api/vehicles'
import { useApi } from './api/useApi'
import { ApiError, isBackendUnavailable } from './api/client'
import type {
  ActivityDTO, ConnectedSystemStatusDTO, RecommendationDTO, TaskDTO, VehicleDetailDTO,
} from './api/types'
import { taskStatusDisplay } from './taskStatus'
import { describeEvent } from './eventDisplay'
import { describeTask } from './taskDisplay'
import { describeRecommendationDetail } from './recommendationDisplay'

// ─── Icons ────────────────────────────────────────────────────────────────────

const I = {
  back:     <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="m15 18-6-6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  vin:      <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="1.75"/><path d="M7 8h10M7 12h10M7 16h6" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></svg>,
  pin:      <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" stroke="currentColor" strokeWidth="1.75"/><circle cx="12" cy="10" r="3" stroke="currentColor" strokeWidth="1.75"/></svg>,
  check:    <svg width="11" height="11" fill="none" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  warn:     <svg width="11" height="11" fill="none" viewBox="0 0 24 24"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/><line x1="12" y1="9" x2="12" y2="13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/><circle cx="12" cy="17" r="0.5" fill="currentColor" stroke="currentColor" strokeWidth="1.2"/></svg>,
  plus:     <svg width="11" height="11" fill="none" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>,
  external: <svg width="11" height="11" fill="none" viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  dismiss:  <svg width="11" height="11" fill="none" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>,
  insights: <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  info:     <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.75"/><path d="M12 8v4M12 16h.01" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></svg>,
  spinner:  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" className="animate-spin"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.2"/><path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/></svg>,
}

// ─── Display-only helpers (no business logic -- just formatting/color) ────────

type Tone = 'green' | 'amber' | 'red' | 'neutral'

function formatDateTime(iso: string): { date: string; time: string } {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return { date: iso, time: '' }
  return {
    date: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }),
    time: d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }),
  }
}

const tekionTone = (s: string | null): Tone =>
  s === null ? 'neutral' : /sold/i.test(s) ? 'amber' : 'green'
const keyperTone = (s: string | null): Tone =>
  s === null ? 'neutral' : s === 'In' ? 'green' : 'amber'
const pairedTone = (s: string | null): Tone =>
  s === null ? 'neutral' : s === 'paired' ? 'green' : 'red'
// mdd_status/recovr_status are stored as 'paired'/'not_paired' -- fine
// as a backend value, not as text a dealership employee should read
// verbatim (the underscore especially).
const pairedLabel = (s: string): string => s === 'paired' ? 'Paired' : 'Not Paired'

const systemColor: Record<string, string> = {
  lot: 'bg-slate-100 text-slate-600',
  tekion: 'bg-blue-50 text-blue-700',
  keyper: 'bg-violet-50 text-violet-700',
  mdd: 'bg-indigo-50 text-indigo-700',
  recovr: 'bg-orange-50 text-orange-700',
  rapidrecon: 'bg-teal-50 text-teal-700',
}

// Source keys are stored lowercase (sync_run.source / event.source);
// these are real product/brand names, so a generic `capitalize` mangles
// three of the five ("Mdd", "Recovr", "Rapidrecon").
const SOURCE_LABEL: Record<string, string> = {
  tekion: 'Tekion', keyper: 'Keyper', mdd: 'MDD', recovr: 'RecovR', rapidrecon: 'RapidRecon', lot: 'Lot',
}
function sourceLabel(source: string): string {
  return SOURCE_LABEL[source] ?? source
}

// See ./taskStatus.ts -- shared with Tasks.tsx so both screens use
// identical end-user wording for the same backend commitment_standing value.
function deriveTaskStatusLabel(t: TaskDTO): string {
  return taskStatusDisplay(t).label
}

const urgencyConfig: Record<string, { bar: string; border: string; bg: string; badge: string; label: string }> = {
  critical: { bar: 'bg-red-500',    border: 'border-red-200',    bg: 'bg-red-50/60',    badge: 'bg-red-100 text-red-700',       label: 'Critical' },
  high:     { bar: 'bg-orange-400', border: 'border-orange-200', bg: 'bg-orange-50/60', badge: 'bg-orange-100 text-orange-700', label: 'High' },
  medium:   { bar: 'bg-amber-400',  border: 'border-amber-200',  bg: 'bg-amber-50/40',  badge: 'bg-amber-100 text-amber-700',   label: 'Medium' },
  low:      { bar: 'bg-slate-300',  border: 'border-slate-200',  bg: 'bg-slate-50',     badge: 'bg-slate-100 text-slate-600',   label: 'Low' },
}

// ─── Left Panel ───────────────────────────────────────────────────────────────

function LeftPanel({ vehicle }: { vehicle: VehicleDetailDTO }) {
  const openCount = vehicle.open_task_count
  const badge = openCount > 0
    ? { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', dot: 'bg-amber-400', label: `${openCount} Open Task${openCount === 1 ? '' : 's'}` }
    : { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', dot: 'bg-emerald-400', label: 'No Open Tasks' }

  return (
    <div className="w-full lg:flex-shrink-0 lg:overflow-y-auto space-y-4 pb-4 lg:w-[268px]" style={{ scrollbarWidth: 'none' }}>
      {/* Vehicle photo -- no backend source of truth yet (API_CONTRACTS.md
          Section 9); placeholder image kept so the layout stays intact,
          real signal (open task count) badged over it instead of an
          invented status label. */}
      <div className="rounded-xl overflow-hidden border border-slate-200 bg-slate-100 relative" style={{ aspectRatio: '16/10' }}>
        <img
          src="https://images.unsplash.com/photo-1623869675781-80aa31012a5a?w=600&h=380&fit=crop&auto=format"
          alt={vehicle.display_name ?? 'Vehicle'}
          className="w-full h-full object-cover"
        />
        <div className="absolute top-2.5 right-2.5">
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold border shadow-sm ${badge.bg} ${badge.text} ${badge.border}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`} />
            {badge.label}
          </span>
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-black/40 to-transparent rounded-b-xl" />
      </div>

      {/* Vehicle identity */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="text-[11px] text-slate-400 font-medium uppercase tracking-wider mb-1">Vehicle</div>
        <h2 className="text-[18px] font-bold text-slate-900 leading-tight tracking-tight">
          {vehicle.display_name || 'Unknown vehicle'}
        </h2>
        {vehicle.new_or_used && <p className="text-[13px] text-slate-500 font-medium mb-3">{vehicle.new_or_used}</p>}

        <div className="space-y-2.5">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 flex-shrink-0">{I.vin}</span>
            <div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">VIN</div>
              <div className="font-mono text-[12px] font-semibold text-slate-800 tracking-wide">{vehicle.vin}</div>
            </div>
          </div>

          <div className="pt-1 border-t border-slate-50">
            <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-0.5">Stock #</div>
            <div className="font-mono text-[15px] font-bold text-blue-600">{vehicle.stock_number ?? '—'}</div>
          </div>
        </div>
      </div>

      {/* Dealership -- real field. Lot zone / days-in-inventory are shown
          honestly as not-yet-tracked rather than invented client-side. */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
        <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Location</div>

        <div className="flex items-start gap-2.5">
          <span className="text-slate-400 mt-0.5 flex-shrink-0">{I.pin}</span>
          <div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wider">Dealership</div>
            <div className="text-[13px] font-semibold text-slate-800">{vehicle.current_dealership_id ?? '—'}</div>
          </div>
        </div>

        <div className="flex items-start gap-2.5 opacity-60">
          <span className="text-slate-400 mt-0.5 flex-shrink-0">{I.info}</span>
          <div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wider">Lot Zone / Inventory Age</div>
            <div className="text-[12px] text-slate-400 italic">Not tracked yet</div>
          </div>
        </div>
      </div>

      {/* System health strip -- derived directly from Vehicle's own
          per-source status fields, no classification invented. */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-3">System Status</div>
        <div className="space-y-2">
          {[
            { label: 'Tekion', value: vehicle.tekion_status, display: vehicle.tekion_status, tone: tekionTone(vehicle.tekion_status) },
            { label: 'Keyper', value: vehicle.keyper_status, display: vehicle.keyper_status, tone: keyperTone(vehicle.keyper_status) },
            { label: 'MDD',    value: vehicle.mdd_status,    display: vehicle.mdd_status && pairedLabel(vehicle.mdd_status),    tone: pairedTone(vehicle.mdd_status) },
            { label: 'RecovR', value: vehicle.recovr_status, display: vehicle.recovr_status && pairedLabel(vehicle.recovr_status), tone: pairedTone(vehicle.recovr_status) },
          ].map(row => (
            <div key={row.label} className="flex items-center justify-between">
              <span className="text-[12px] text-slate-600">{row.label}</span>
              {row.value === null
                ? <span className="text-slate-300 text-[11px]">—</span>
                : row.tone === 'green'
                ? <span className="flex items-center gap-1 text-emerald-600 text-[11px] font-semibold">{I.check} {row.display}</span>
                : row.tone === 'red'
                ? <span className="text-red-600 text-[11px] font-semibold">{row.display}</span>
                : <span className="text-amber-600 text-[11px] font-semibold">{row.display}</span>
              }
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Timeline ─────────────────────────────────────────────────────────────────

// Demo Polish: the backend returns timeline events in insertion order
// (event_id DESC -- an audit-trail ordering, see queries/dashboard.py's
// recent_activity_feed), not the order things actually happened in. A
// vehicle whose data arrived out of chronological order (e.g. a later
// sync re-adds a "Stocked In" event for an earlier date) could show a
// Timeline whose dates visibly ran backwards. Sorted here by each
// event's own real timestamp (event_time when the source provided one,
// else observed_at) so the story reads newest-to-oldest by when it
// happened, not by when LotSync happened to write it down.
function sortEventsByWhenTheyHappened(events: ActivityDTO[]): ActivityDTO[] {
  return [...events].sort((a, b) => {
    const at = a.event_time ?? a.observed_at
    const bt = b.event_time ?? b.observed_at
    return new Date(bt).getTime() - new Date(at).getTime()
  })
}

function Timeline({ events }: { events: ActivityDTO[] }) {
  const sorted = useMemo(() => sortEventsByWhenTheyHappened(events), [events])

  return (
    <div className="w-full lg:flex-1 flex flex-col lg:overflow-hidden min-w-0">
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div>
          <h3 className="text-[15px] font-bold text-slate-900">Vehicle Timeline</h3>
          <p className="text-[12px] text-slate-400 mt-0.5">{events.length} event{events.length === 1 ? '' : 's'}</p>
        </div>
        <button disabled title="Coming soon"
          className="text-[11px] font-semibold text-blue-300 bg-blue-50/50 border border-blue-100 px-3 py-1.5 rounded-lg flex items-center gap-1.5 cursor-not-allowed">
          {I.plus} Log Event
        </button>
      </div>

      <div className="lg:flex-1 lg:overflow-y-auto pr-1" style={{ scrollbarWidth: 'thin' }}>
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-slate-400">
            <p className="text-[13px] font-medium">No activity recorded yet</p>
          </div>
        ) : (
          <div className="relative pb-4">
            <div className="absolute left-4 top-2 bottom-2 w-px bg-slate-200" />
            <div className="space-y-0">
              {sorted.map((ev) => {
                const { date, time } = formatDateTime(ev.event_time ?? ev.observed_at)
                const { title, detail } = describeEvent(ev)
                return (
                  <div key={ev.event_id} className="relative flex gap-4 group">
                    <div className="flex-shrink-0 relative z-10 mt-3">
                      <div className="w-8 h-8 rounded-full border-2 flex items-center justify-center bg-blue-400 border-blue-100">
                        <span className="w-1.5 h-1.5 rounded-full bg-white block" />
                      </div>
                    </div>
                    <div className="flex-1 min-w-0 mb-1 rounded-xl p-3.5 transition-all duration-150 group-hover:shadow-sm bg-white border border-slate-100 group-hover:border-slate-200">
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${systemColor[ev.source] ?? 'bg-slate-100 text-slate-600'}`}>
                          {sourceLabel(ev.source)}
                        </span>
                        <div className="text-right flex-shrink-0">
                          <div className="text-[10px] font-mono text-slate-400">{date}</div>
                          {time && <div className="text-[10px] font-mono text-slate-500 font-semibold">{time}</div>}
                        </div>
                      </div>
                      <p className="text-[13px] font-bold leading-snug text-slate-900">
                        {title}
                      </p>
                      {detail && (
                        <p className="text-[11px] text-slate-400 leading-snug mt-0.5">{detail}</p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── System Cards (Connected Systems) ──────────────────────────────────────────

function SysCardHeader({ name, status, tone }: { name: string; status: string; tone: Tone }) {
  const styles: Record<Tone, string> = {
    green:   'bg-emerald-50 text-emerald-700 border-emerald-200',
    amber:   'bg-amber-50 text-amber-700 border-amber-200',
    red:     'bg-red-50 text-red-700 border-red-200',
    neutral: 'bg-slate-50 text-slate-700 border-slate-200',
  }
  const dots: Record<Tone, string> = { green: 'bg-emerald-400', amber: 'bg-amber-400', red: 'bg-red-500', neutral: 'bg-slate-400' }
  return (
    <div className={`flex items-center justify-between px-4 py-2.5 border-b ${styles[tone]}`}>
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${dots[tone]}`} />
        <span className="text-[13px] font-bold">{sourceLabel(name)}</span>
      </div>
      <div className="flex items-center gap-1.5">
        {/* CSS capitalize only touches the first letter of each
            whitespace-separated word -- "in_progress" has no spaces, so
            without the replace this rendered as "In_progress" verbatim. */}
        <span className="text-[11px] font-semibold capitalize">{status.replace(/_/g, ' ')}</span>
        <button className="opacity-50 hover:opacity-100 transition-opacity">{I.external}</button>
      </div>
    </div>
  )
}

function SysRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-[11px] text-slate-400">{label}</span>
      <span className={`text-[12px] font-semibold text-slate-800 ${mono ? 'font-mono text-[11px]' : ''}`}>{value}</span>
    </div>
  )
}

const syncStatusTone = (status: string): Tone =>
  status === 'complete' ? 'green' : status === 'failed' ? 'red' : status === 'delayed' ? 'amber' : 'neutral'

function SystemCards({ connectedSystems }: { connectedSystems: Record<string, ConnectedSystemStatusDTO> }) {
  const entries = Object.entries(connectedSystems)

  return (
    <div className="w-full lg:flex-shrink-0 lg:overflow-y-auto pb-4 space-y-3 lg:w-[288px]" style={{ scrollbarWidth: 'none' }}>
      <div className="flex items-center justify-between flex-shrink-0">
        <h3 className="text-[15px] font-bold text-slate-900">Connected Systems</h3>
        <span className="text-[10px] text-slate-400">{entries.length} integration{entries.length === 1 ? '' : 's'}</span>
      </div>

      {entries.length === 0 ? (
        <div className="text-[12px] text-slate-400 py-2">No sync history yet for this vehicle.</div>
      ) : entries.map(([source, sys]) => {
        const { date, time } = formatDateTime(sys.started_at)
        return (
          <div key={source} className="bg-white rounded-xl border border-slate-200 overflow-hidden hover:shadow-sm transition-shadow">
            <SysCardHeader name={source} status={sys.status} tone={syncStatusTone(sys.status)} />
            <div className="px-4 py-2 divide-y divide-slate-50">
              <SysRow label="Last Sync" value={`${date} ${time}`.trim()} />
              {sys.records_processed !== null && (
                <SysRow label="Records Processed" value={String(sys.records_processed)} mono />
              )}
            </div>
          </div>
        )
      })}

      <div className="flex items-start gap-2 px-1 pt-1">
        <span className="text-slate-400 flex-shrink-0 mt-0.5">{I.info}</span>
        <p className="text-[10px] text-slate-400 leading-relaxed">
          Inventory data is refreshed during scheduled Inventory Syncs. Some connected system information may be up to a few hours behind real time.
        </p>
      </div>
    </div>
  )
}

// ─── Tasks -- the direct answer to "why is this vehicle on the task list" ──────
//
// VehicleDetailDTO.tasks was already fetched (api/routers/vehicles.py) and
// typed here, but never rendered -- this screen showed only the LeftPanel's
// "N Open Tasks" count, with no way to see which tasks or why. Timeline
// events give an indirect clue (e.g. a "RecovR: not_paired" event) but
// never the Task's own task_type/reason/priority. Added per PRODUCT.md's
// own Vehicle Detail ordering: identity, connected systems, timeline,
// Tasks, Recommendations.

function TasksPanel({ tasks }: { tasks: TaskDTO[] }) {
  const outstanding = tasks.filter(t => t.commitment_standing === 'outstanding')

  return (
    <div className="flex-shrink-0 border-t border-slate-200 bg-white px-4 sm:px-5 py-4">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className="text-blue-500">{I.insights}</span>
        <span className="text-[12px] font-bold text-slate-700 uppercase tracking-wider">Tasks</span>
        <span className="text-[10px] font-bold text-amber-600 bg-amber-50 border border-amber-100 px-1.5 py-0.5 rounded-full">
          {outstanding.length} open
        </span>
      </div>

      {tasks.length === 0 ? (
        <div className="flex items-center gap-2 py-3 text-[12px] text-slate-400">
          <span className="text-emerald-500">{I.check}</span> No tasks for this vehicle right now.
        </div>
      ) : (
        // Below lg: cards stack full-width (no horizontal scroll). lg+:
        // original horizontal-scrolling row, unchanged.
        <div className="flex flex-col lg:flex-row gap-3 lg:overflow-x-auto pb-1" style={{ scrollbarWidth: 'none' }}>
          {tasks.map((task) => {
            // Demo Polish: no rule assigns Task.priority yet, so most tasks
            // have priority=None -- coercing that to 'low' rendered a
            // confident "Low" badge implying a classification that never
            // happened. Styling still falls back to the neutral/low
            // treatment; the text label itself only shows when real.
            const uc = task.priority ? (urgencyConfig[task.priority.toLowerCase()] ?? urgencyConfig.low) : urgencyConfig.low
            const display = describeTask(task)
            return (
              <div key={task.task_id} className={`w-full lg:w-64 lg:flex-shrink-0 rounded-xl border p-3.5 ${uc.border} ${uc.bg}`}>
                <div className={`h-0.5 w-full rounded-full mb-3 ${uc.bar}`} />
                <div className="flex items-center gap-1.5 mb-1.5 flex-wrap">
                  {task.priority && <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${uc.badge}`}>{uc.label}</span>}
                  <span className="text-[10px] font-semibold text-slate-500">{deriveTaskStatusLabel(task)}</span>
                </div>
                <p className="text-[12px] font-bold text-slate-900 leading-snug mb-1">{display.title}</p>
                <p className="text-[11px] text-slate-500 leading-relaxed">{display.description}</p>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Operational Insights (Recommendations) ────────────────────────────────────

function OperationalInsights({ recommendations }: { recommendations: RecommendationDTO[] }) {
  const [dismissedLocally, setDismissedLocally] = useState<Set<number>>(new Set())
  const open = recommendations.filter(r => r.status === 'open' && !dismissedLocally.has(r.recommendation_id))

  return (
    <div className="flex-shrink-0 border-t border-slate-200 bg-white px-4 sm:px-5 py-4">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className="text-blue-500">{I.insights}</span>
        <span className="text-[12px] font-bold text-slate-700 uppercase tracking-wider">Operational Insights</span>
        <span className="text-[10px] font-bold text-blue-600 bg-blue-50 border border-blue-100 px-1.5 py-0.5 rounded-full">
          {open.length} active
        </span>
      </div>

      {open.length === 0 ? (
        <div className="flex items-center gap-2 py-3 text-[12px] text-slate-400">
          <span className="text-emerald-500">{I.check}</span> No active insights — vehicle is operationally on track.
        </div>
      ) : (
        // Below lg: cards stack full-width (no horizontal scroll). lg+:
        // original horizontal-scrolling row, unchanged.
        <div className="flex flex-col lg:flex-row gap-3 lg:overflow-x-auto pb-1" style={{ scrollbarWidth: 'none' }}>
          {open.map((rec) => {
            // Demo Polish: same fix as TasksPanel above -- don't coerce a
            // missing severity into a confident "Low" label.
            const uc = rec.severity ? (urgencyConfig[rec.severity.toLowerCase()] ?? urgencyConfig.low) : urgencyConfig.low
            return (
              <div key={rec.recommendation_id} className={`w-full lg:w-64 lg:flex-shrink-0 rounded-xl border p-3.5 ${uc.border} ${uc.bg}`}>
                <div className={`h-0.5 w-full rounded-full mb-3 ${uc.bar}`} />
                <div className="flex items-center gap-1.5 mb-1.5">
                  {rec.severity && <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${uc.badge}`}>{uc.label}</span>}
                </div>
                {/* rule_source (e.g. "key_out_aging") is a backend rule
                    identifier, not display copy -- rec.title is always
                    set by the one recommendation this project currently
                    generates, but this stays a safe fallback rather than
                    ever showing that raw identifier if a future rule
                    forgets to set one. */}
                <p className="text-[12px] font-bold text-slate-900 leading-snug mb-1">{rec.title ?? 'Recommendation'}</p>
                {describeRecommendationDetail(rec) && (
                  <p className="text-[11px] text-slate-500 leading-relaxed mb-3">{describeRecommendationDetail(rec)}</p>
                )}
                <div className="flex items-center gap-1.5 flex-wrap">
                  <button disabled title="Coming soon -- write APIs are out of this sprint's scope"
                    className="text-[11px] font-bold px-2.5 py-1 rounded-md border border-blue-200 bg-white text-blue-300 cursor-not-allowed flex items-center gap-1">
                    {I.plus} Create Task
                  </button>
                  <button onClick={() => setDismissedLocally(d => new Set(d).add(rec.recommendation_id))}
                    title="Local-only for now -- Dismiss write API is out of this sprint's scope"
                    className="text-[11px] font-bold px-2.5 py-1 rounded-md border border-slate-200 bg-white text-slate-400 hover:text-slate-600 hover:border-slate-300 transition-all duration-150 flex items-center gap-1">
                    {I.dismiss} Dismiss
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Loading / Error / Not-found states ────────────────────────────────────────

function CenteredMessage({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-slate-400">{children}</div>
    </div>
  )
}

// ─── Vehicle Detail Page ──────────────────────────────────────────────────────

export default function VehicleDetailPage({ vin, onBack, backLabel = 'Dashboard' }: {
  vin: string; onBack: () => void; backLabel?: string
}) {
  const state = useApi(() => getVehicleDetail(vin), [vin])

  return (
    // Below lg the whole page scrolls as one column (breadcrumb + stacked
    // panels + Tasks/Insights rows); lg+ is the original desktop shape --
    // no page-level scroll, each panel scrolls its own bounded region.
    <div className="flex-1 flex flex-col overflow-y-auto lg:overflow-hidden min-h-0">
      {/* Breadcrumb */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 sm:px-5 py-2.5 border-b border-slate-200 bg-white flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <button onClick={onBack}
            className="flex items-center gap-1.5 text-[12px] font-semibold text-slate-500 hover:text-slate-800 transition-colors group">
            <span className="group-hover:-translate-x-0.5 transition-transform">{I.back}</span>
            {backLabel}
          </button>
          <span className="text-slate-300">/</span>
          <span className="text-[12px] font-bold text-slate-900">
            {state.status === 'success'
              ? `Stock ${state.data.stock_number ?? '—'} · ${state.data.display_name ?? 'Unknown vehicle'}`
              : vin}
          </span>
        </div>

        {state.status === 'success' && (
          <div className="flex items-center gap-2">
            <button className="text-[11px] font-bold text-slate-600 bg-white border border-slate-200 hover:border-slate-300 px-3 py-1.5 rounded-lg transition-colors" disabled title="Coming soon">
              Edit Vehicle
            </button>
            <button className="text-[11px] font-bold text-white bg-blue-300 px-3 py-1.5 rounded-lg flex items-center gap-1.5 cursor-not-allowed" disabled title="Coming soon -- write APIs are out of this sprint's scope">
              {I.plus} Create Task
            </button>
          </div>
        )}
      </div>

      {state.status === 'loading' && (
        <CenteredMessage>
          {I.spinner}
          <p className="text-[13px] font-medium">Loading vehicle…</p>
        </CenteredMessage>
      )}

      {state.status === 'error' && state.error instanceof ApiError && state.error.status === 404 && (
        <CenteredMessage>
          <p className="text-[13px] font-medium">No vehicle found for VIN "{vin}".</p>
        </CenteredMessage>
      )}

      {state.status === 'error' && !(state.error instanceof ApiError && state.error.status === 404) && (
        <CenteredMessage>
          <p className="text-[13px] font-medium text-red-500">
            {isBackendUnavailable(state.error) ? 'The LotSync API is unreachable.' : 'Something went wrong loading this vehicle.'}
          </p>
          <p className="text-[11px] text-slate-400">{state.error.message}</p>
        </CenteredMessage>
      )}

      {state.status === 'success' && (
        <>
          {/* flex-shrink-0 below lg is load-bearing: the root above is
              overflow-y-auto expecting to grow to full content height, but
              this row's ancestor chain still gives it a bounded height at
              that breakpoint. Without shrink-0, flexbox squeezes this row
              (and LeftPanel/Timeline/SystemCards inside it) below their
              content height instead of letting overflow-y-auto do its job
              -- content still paints at full size (nothing here clips it)
              but at the WRONG position, visually overlapping TasksPanel/
              OperationalInsights below. lg:flex-1 restores the original
              fill-remaining-space behavior once the root is overflow-hidden
              again and genuinely bounded. */}
          <div className="flex-shrink-0 flex flex-col lg:flex-row lg:flex-1 gap-5 px-4 sm:px-5 pt-4 lg:overflow-hidden min-h-0">
            <LeftPanel vehicle={state.data} />
            <Timeline events={state.data.timeline} />
            <SystemCards connectedSystems={state.data.connected_systems} />
          </div>
          <TasksPanel tasks={state.data.tasks} />
          <OperationalInsights recommendations={state.data.recommendations} />
        </>
      )}
    </div>
  )
}
