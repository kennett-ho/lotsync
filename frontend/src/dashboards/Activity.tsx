// Activity.tsx — global Activity Log
//
// Sprint 3 (Frontend Integration): wired to GET /activity (ActivityDTO[]
// per API_CONTRACTS.md). See PHASE_3_SPRINT_3_REVIEW.md for the full
// account of what changed relative to the original mockup.
//
// Several mockup fields have no backend equivalent and are not
// fabricated here:
// - `actor` (a resolved human name like "Marcus Torres") -- the backend
//   only carries `actor_employee_id` (an id string, e.g. "emp-0142"),
//   and no employee-lookup endpoint exists yet to resolve it to a
//   display name (API_CONTRACTS.md Section 9 already names this gap).
//   The raw id is shown instead of a fabricated name.
// - `status` (Verified/Waiting Sync/Exception/...) -- DATA_MODEL.md's
//   Event has no status field at all; it's an immutable, append-only
//   record. The mockup's per-row status pill is dropped rather than
//   invented.
// - `type` (a cosmetic icon taxonomy) -- replaced with `source`
//   (tekion/keyper/mdd/recovr/rapidrecon/lot), the real, small,
//   DATA_MODEL.md-governed vocabulary, rather than guessing a mapping
//   from the backend's actual event_type strings onto the mockup's
//   invented categories.
// The "Employee" and "Verification" sidebar filters are replaced with
// "Source" and "Actor" (the real fields available), and "Date Range"
// is kept, computed honestly from each event's real observed_at.
//
// GET /activity has no server-side search or offset pagination yet
// (a known Sprint 2 compromise, same as Vehicles List) -- this screen
// fetches a generous page and filters/searches client-side over it,
// the same pattern already used for Vehicles List.

import { useMemo, useState } from 'react'
import { getActivity } from '../api/activity'
import { useApi } from '../api/useApi'
import { isBackendUnavailable } from '../api/client'
import type { ActivityDTO } from '../api/types'

const ACTIVITY_LIMIT = 200

// ─── Source vocabulary (real, per DATA_MODEL.md) ───────────────────────────────

const SOURCES = ['tekion', 'keyper', 'mdd', 'recovr', 'rapidrecon', 'lot'] as const

const sourceIconColor: Record<string, string> = {
  tekion: 'text-blue-600',
  keyper: 'text-violet-600',
  mdd: 'text-indigo-600',
  recovr: 'text-orange-600',
  rapidrecon: 'text-teal-600',
  lot: 'text-slate-500',
}

function SourceIcon({ source }: { source: string }) {
  const color = sourceIconColor[source] ?? 'text-slate-500'
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" className={color}>
      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" />
      <path d="M5.5 8l1.5 1.5L10.5 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function IconSearch() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" className="text-slate-400">
      <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M11 11l3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

function IconGear() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" className="text-white">
      <path d="M8 10a2 2 0 100-4 2 2 0 000 4z" stroke="currentColor" strokeWidth="1.4" />
      <path
        d="M13.3 8c0-.3 0-.6-.1-.9l1.4-1.1-1.4-2.4-1.7.7c-.5-.4-1-.7-1.6-.9L9.5 2h-3l-.4 1.4c-.6.2-1.1.5-1.6.9l-1.7-.7L1.4 6 2.8 7.1c0 .3-.1.6-.1.9s0 .6.1.9L1.4 10l1.4 2.4 1.7-.7c.5.4 1 .7 1.6.9L6.5 14h3l.4-1.4c.6-.2 1.1-.5 1.6-.9l1.7.7L14.6 10l-1.4-1.1c.1-.3.1-.6.1-.9z"
        stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  )
}

function Avatar({ actorId, isSystem }: { actorId: string | null; isSystem: boolean }) {
  if (isSystem) {
    return (
      <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
        <IconGear />
      </div>
    )
  }
  const initials = (actorId ?? '??').replace(/^emp-/, '').slice(0, 2).toUpperCase()
  return (
    <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-slate-400">
      <span className="text-[11px] font-semibold text-white leading-none">{initials}</span>
    </div>
  )
}

function formatDateTime(iso: string): { date: string; time: string; group: 'today' | 'yesterday' | 'this-week' | 'older' } {
  const d = new Date(iso)
  const now = new Date()
  const startOfDay = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate())
  const diffDays = Math.round((startOfDay(now).getTime() - startOfDay(d).getTime()) / 86400000)
  const group = diffDays <= 0 ? 'today' : diffDays === 1 ? 'yesterday' : diffDays <= 7 ? 'this-week' : 'older'
  return {
    date: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    time: Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }),
    group,
  }
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function ActivityRow({ entry, onVehicleSelect }: { entry: ActivityDTO; onVehicleSelect: (vin: string) => void }) {
  const isSystem = entry.actor_employee_id === null
  const { time } = formatDateTime(entry.observed_at)
  return (
    <div className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors min-h-[52px]">
      <Avatar actorId={entry.actor_employee_id} isSystem={isSystem} />
      <div className="flex-shrink-0 w-5 flex items-center justify-center">
        <SourceIcon source={entry.source} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[13px] font-semibold text-slate-800 whitespace-nowrap capitalize">
            {isSystem ? entry.source : entry.actor_employee_id}
          </span>
          <span className="text-[13px] text-slate-500">{entry.summary ?? entry.event_type}</span>
          {entry.vehicle?.stock_number && (
            <button onClick={() => entry.vehicle && onVehicleSelect(entry.vehicle.vin)}
              className="font-mono text-[11px] bg-slate-100 hover:bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded transition-colors">
              #{entry.vehicle.stock_number}
            </button>
          )}
        </div>
      </div>
      <div className="flex-shrink-0 w-16 text-right">
        <span className="text-[12px] text-slate-400 whitespace-nowrap">{time}</span>
      </div>
    </div>
  )
}

function DateGroupCard({ label, entries, onVehicleSelect }: {
  label: string; entries: ActivityDTO[]; onVehicleSelect: (vin: string) => void
}) {
  if (entries.length === 0) return null
  return (
    <div>
      <div className="text-[12px] font-semibold text-slate-400 uppercase tracking-wider mb-2 px-1">{label}</div>
      <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100 overflow-hidden">
        {entries.map(entry => <ActivityRow key={entry.event_id} entry={entry} onVehicleSelect={onVehicleSelect} />)}
      </div>
    </div>
  )
}

function SidebarSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">{title}</div>
      {children}
    </div>
  )
}

function FilterButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick}
      className={`text-left px-2 py-1.5 rounded-lg text-[13px] transition-colors capitalize ${
        active ? 'bg-blue-50 text-blue-700 font-medium' : 'text-slate-600 hover:bg-slate-50'
      }`}>
      {label}
    </button>
  )
}

type DateFilter = 'all' | 'today' | 'yesterday' | 'this-week'

const spinner = (
  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" className="animate-spin">
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.2" />
    <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
  </svg>
)

// ─── Main Component ───────────────────────────────────────────────────────────

export default function Activity({ onVehicleSelect }: { onVehicleSelect: (vin: string) => void }) {
  const state = useApi(() => getActivity({ limit: ACTIVITY_LIMIT }), [])

  const [search, setSearch] = useState('')
  const [sourceFilter, setSourceFilter] = useState<string>('all')
  const [actorFilter, setActorFilter] = useState<string>('all')
  const [dateFilter, setDateFilter] = useState<DateFilter>('all')

  const activities = state.status === 'success' ? state.data : []

  const actorOptions = useMemo(() => {
    const ids = new Set(activities.filter(a => a.actor_employee_id !== null).map(a => a.actor_employee_id as string))
    return ['all', ...Array.from(ids).sort()]
  }, [activities])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return activities.filter(e => {
      if (q) {
        const searchable = [e.actor_employee_id ?? '', e.summary ?? '', e.event_type, e.vehicle?.stock_number ?? '', e.vehicle?.vin ?? '']
          .join(' ').toLowerCase()
        if (!searchable.includes(q)) return false
      }
      if (sourceFilter !== 'all' && e.source !== sourceFilter) return false
      if (actorFilter !== 'all' && e.actor_employee_id !== actorFilter) return false
      if (dateFilter !== 'all' && formatDateTime(e.observed_at).group !== dateFilter) return false
      return true
    })
  }, [activities, search, sourceFilter, actorFilter, dateFilter])

  const groupsToShow = useMemo(() => {
    const byGroup: Record<string, ActivityDTO[]> = { today: [], yesterday: [], 'this-week': [], older: [] }
    for (const e of filtered) byGroup[formatDateTime(e.observed_at).group].push(e)
    return [
      { label: 'Today', entries: byGroup.today },
      { label: 'Yesterday', entries: byGroup.yesterday },
      { label: 'Earlier This Week', entries: byGroup['this-week'] },
      { label: 'Older', entries: byGroup.older },
    ].filter(g => g.entries.length > 0)
  }, [filtered])

  return (
    <div className="flex h-full bg-slate-50 min-h-screen">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-slate-200 flex flex-col gap-5 p-4 flex-shrink-0 overflow-y-auto">
        <div className="relative">
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none"><IconSearch /></span>
          <input type="text" placeholder="Search activities…" value={search} onChange={e => setSearch(e.target.value)}
            className="w-full pl-7 pr-3 py-1.5 text-[13px] bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-200 placeholder:text-slate-400 text-slate-700" />
        </div>

        <SidebarSection title="Source">
          <div className="flex flex-col gap-0.5">
            <FilterButton label="All" active={sourceFilter === 'all'} onClick={() => setSourceFilter('all')} />
            {SOURCES.map(s => (
              <FilterButton key={s} label={s} active={sourceFilter === s} onClick={() => setSourceFilter(s)} />
            ))}
          </div>
        </SidebarSection>

        <SidebarSection title="Actor">
          <div className="flex flex-col gap-0.5">
            {actorOptions.map(a => (
              <FilterButton key={a} label={a === 'all' ? 'All' : a} active={actorFilter === a} onClick={() => setActorFilter(a)} />
            ))}
          </div>
        </SidebarSection>

        <SidebarSection title="Date Range">
          <div className="flex flex-col gap-0.5">
            {(['today', 'yesterday', 'this-week', 'all'] as DateFilter[]).map(d => (
              <FilterButton key={d} label={d === 'all' ? 'All time' : d.replace('-', ' ')} active={dateFilter === d} onClick={() => setDateFilter(d)} />
            ))}
          </div>
        </SidebarSection>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-[20px] font-bold text-slate-800">Activity Log</h1>
            <p className="text-[13px] text-slate-400 mt-0.5">Everything that happened on the lot</p>
          </div>
          {state.status === 'success' && (
            <div className="text-[13px] text-slate-500">
              Showing <span className="font-semibold text-slate-700">{filtered.length}</span> of{' '}
              <span className="font-semibold text-slate-700">{activities.length}</span> activities
            </div>
          )}
        </div>

        {state.status === 'loading' && (
          <div className="flex flex-col items-center justify-center py-24 text-slate-400 gap-3">
            {spinner}
            <p className="text-[13px] font-medium">Loading activity…</p>
          </div>
        )}

        {state.status === 'error' && (
          <div className="flex flex-col items-center justify-center py-24 text-center gap-2">
            <p className="text-[15px] font-medium text-red-500">
              {isBackendUnavailable(state.error) ? 'The LotSync API is unreachable.' : 'Something went wrong loading activity.'}
            </p>
            <p className="text-[13px] text-slate-400">{state.error.message}</p>
          </div>
        )}

        {state.status === 'success' && groupsToShow.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mb-3">
              <IconSearch />
            </div>
            <p className="text-[15px] font-medium text-slate-600">
              {activities.length === 0 ? 'No activity recorded yet' : 'No activities found'}
            </p>
            {activities.length > 0 && (
              <p className="text-[13px] text-slate-400 mt-1">Try adjusting your filters or search query</p>
            )}
          </div>
        )}

        {state.status === 'success' && groupsToShow.length > 0 && (
          <div className="flex flex-col gap-6">
            {groupsToShow.map(g => (
              <DateGroupCard key={g.label} label={g.label} entries={g.entries} onVehicleSelect={onVehicleSelect} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
