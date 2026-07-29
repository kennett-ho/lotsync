// VehiclesList.tsx — Lot operational inventory board
//
// Sprint 3 (Frontend Integration): wired to GET /vehicles (VehicleDTO[]
// per API_CONTRACTS.md). See PHASE_3_SPRINT_3_REVIEW.md for a full
// account of what changed relative to the original mockup and why.
//
// The mockup's single composite `status` (Ready / Needs Tracker / In
// Recon / Keys Out / Needs Attention) has no backend equivalent --
// DATA_MODEL.md's Vehicle has no such field, and API_CONTRACTS.md
// Section 9 already names this as an open question ("no canonical,
// backend-computed Vehicle operational-status enum yet"). Inventing
// that classification here would duplicate business-rule judgment in
// React, which this sprint's architecture rules explicitly forbid.
// Filters below instead read real per-source fields directly (Keys
// Out, RecovR Missing, MDD Missing, Has Open Tasks) -- exactly what
// this file's own comment already anticipated before this sprint
// ("filters will be generated from backend operational state").
// `trim`, `color`, `zone`, `inventoryAge`, and `lastSyncHours` are
// dropped for the same reason: none exist anywhere in DATA_MODEL.md's
// Vehicle shape, so none are fabricated client-side.

import { useMemo, useState } from 'react'
import { getVehicles } from '../api/vehicles'
import { useApi } from '../api/useApi'
import { isBackendUnavailable } from '../api/client'
import type { VehicleDTO } from '../api/types'

// ─── Filters (direct reads of real fields -- see header note) ─────────────────

type FilterKey = 'all' | 'keys-out' | 'recovr-missing' | 'mdd-missing' | 'open-tasks'

const FILTERS: { key: FilterKey; label: string; test: (v: VehicleDTO) => boolean }[] = [
  { key: 'all',            label: 'All',            test: () => true },
  { key: 'keys-out',       label: 'Keys Out',       test: v => v.keyper_status !== null && v.keyper_status !== 'In' },
  { key: 'recovr-missing', label: 'RecovR Missing', test: v => v.recovr_status !== null && v.recovr_status !== 'paired' },
  { key: 'mdd-missing',    label: 'MDD Missing',    test: v => v.mdd_status !== null && v.mdd_status !== 'paired' },
  { key: 'open-tasks',     label: 'Has Open Tasks', test: v => v.open_task_count > 0 },
]

// ─── Sub-components ───────────────────────────────────────────────────────────

type SortKey = 'stock_number' | 'make' | 'current_dealership_id' | 'open_task_count'

function ColHeader({ label, sortKey, current, dir, onSort, right }: {
  label: string; sortKey: SortKey; current: SortKey; dir: 'asc' | 'desc'
  onSort: (k: SortKey) => void; right?: boolean
}) {
  const active = current === sortKey
  return (
    <button onClick={() => onSort(sortKey)}
      className={`flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider transition-colors ${right ? 'ml-auto' : ''} ${
        active ? 'text-blue-600' : 'text-slate-400 hover:text-slate-600'
      }`}>
      {label}
      <svg width="8" height="8" fill="none" viewBox="0 0 24 24"
        className={`transition-transform ${active && dir === 'desc' ? 'rotate-180' : ''} ${active ? 'opacity-100' : 'opacity-25'}`}>
        <path d="M12 5v14M5 12l7-7 7 7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    </button>
  )
}

function Highlight({ text, query }: { text: string; query: string }) {
  if (!query) return <>{text}</>
  const idx = text.toLowerCase().indexOf(query.toLowerCase())
  if (idx === -1) return <>{text}</>
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-blue-100 text-blue-800 rounded-sm">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  )
}

// Compact tri-state system indicator -- driven directly by a raw per-source field.
function SysBadge({ label, value, okValue }: { label: string; value: string | null; okValue: string }) {
  const state: 'ok' | 'warn' | 'unknown' = value === null ? 'unknown' : value === okValue ? 'ok' : 'warn'
  const styles = {
    ok:      'bg-slate-100 text-slate-400',
    warn:    'bg-amber-50 text-amber-600 border border-amber-200',
    unknown: 'bg-slate-50 text-slate-300 border border-slate-100',
  }
  const dot = { ok: 'bg-emerald-400', warn: 'bg-amber-400', unknown: 'bg-slate-300' }
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-md ${styles[state]}`}>
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dot[state]}`} />
      {label}
    </span>
  )
}

function TasksBadge({ count }: { count: number }) {
  if (count === 0) return <span className="text-[11px] text-slate-300 font-medium tabular-nums">—</span>
  const style = count >= 3
    ? 'bg-red-100 text-red-700 border border-red-200'
    : 'bg-amber-50 text-amber-700 border border-amber-200'
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full ${style}`}>
      {count >= 3 && (
        <svg width="9" height="9" fill="none" viewBox="0 0 24 24"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/><line x1="12" y1="9" x2="12" y2="13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
      )}
      {count} open
    </span>
  )
}

// ─── Vehicle row ──────────────────────────────────────────────────────────────

function VehicleRow({ v, query, selected, onToggle, onSelect }: {
  v: VehicleDTO; query: string; selected: boolean
  onToggle: (vin: string) => void
  onSelect: (vin: string) => void
}) {
  return (
    <tr className={`group border-b border-slate-100 transition-colors ${
      selected ? 'bg-blue-50' : 'hover:bg-slate-50/70'
    }`}>
      <td className="pl-4 pr-3 py-3 w-8">
        <input type="checkbox" checked={selected} onChange={() => onToggle(v.vin)}
          className="w-3.5 h-3.5 rounded border-slate-300 text-blue-600 cursor-pointer accent-blue-600" />
      </td>

      <td className="py-3 pr-5 w-24">
        <button onClick={() => onSelect(v.vin)}
          className="font-mono text-[12px] font-bold text-blue-600 hover:text-blue-800 hover:underline transition-colors">
          <Highlight text={v.stock_number ?? '—'} query={query} />
        </button>
      </td>

      <td className="py-3 pr-5" style={{ width: '220px' }}>
        <button onClick={() => onSelect(v.vin)} className="text-left block w-full">
          <div className="text-[13px] font-semibold text-slate-900 group-hover:text-blue-700 transition-colors leading-snug">
            <Highlight text={v.display_name || 'Unknown vehicle'} query={query} />
          </div>
          {v.new_or_used && <div className="text-[11px] text-slate-400 mt-0.5">{v.new_or_used}</div>}
        </button>
      </td>

      <td className="py-3 pr-5" style={{ width: '160px' }}>
        <span className="font-mono text-[11px] text-slate-400 tracking-wide">
          <Highlight text={v.vin} query={query} />
        </span>
      </td>

      <td className="py-3 pr-5" style={{ width: '120px' }}>
        <span className="text-[12px] text-slate-600">
          <Highlight text={v.current_dealership_id ?? '—'} query={query} />
        </span>
      </td>

      <td className="py-3 pr-5 w-20 text-center">
        <TasksBadge count={v.open_task_count} />
      </td>

      <td className="py-3 px-5">
        <div className="flex items-center justify-center gap-1.5">
          <SysBadge label="RecovR" value={v.recovr_status} okValue="paired" />
          <SysBadge label="MDD"    value={v.mdd_status}    okValue="paired" />
          <SysBadge label="Keys"   value={v.keyper_status}  okValue="In" />
        </div>
      </td>
    </tr>
  )
}

// ─── Bulk action toolbar ──────────────────────────────────────────────────────

function BulkToolbar({ count, onClear }: { count: number; onClear: () => void }) {
  const actions = ['Create Task', 'Move Zone', 'Log Activity', 'Export'] as const
  return (
    <div className="flex items-center gap-3 px-5 py-2 bg-blue-600 text-white">
      <span className="text-[13px] font-bold">{count} vehicle{count !== 1 ? 's' : ''} selected</span>
      <div className="w-px h-4 bg-white/25" />
      <div className="flex items-center gap-2">
        {actions.map(a => (
          <button key={a} disabled
            className="text-[11px] font-bold px-3 py-1 rounded-md bg-white/10 text-white/50 border border-white/15 cursor-not-allowed"
            title="Coming soon">
            {a}
          </button>
        ))}
      </div>
      <div className="flex-1" />
      <button onClick={onClear}
        className="text-[11px] font-semibold text-white/70 hover:text-white transition-colors flex items-center gap-1">
        <svg width="11" height="11" fill="none" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
        Clear
      </button>
    </div>
  )
}

// ─── Loading / error states ────────────────────────────────────────────────────

function CenteredMessage({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-slate-400">{children}</div>
    </div>
  )
}

const spinner = (
  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" className="animate-spin">
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.2"/>
    <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
  </svg>
)

// ─── Main component ───────────────────────────────────────────────────────────

export default function VehiclesList({ onVehicleSelect }: { onVehicleSelect: (vin: string) => void }) {
  const state = useApi(() => getVehicles(), [])

  const [search,   setSearch]   = useState('')
  const [filter,   setFilter]   = useState<FilterKey>('all')
  const [sortKey,  setSortKey]  = useState<SortKey>('open_task_count')
  const [sortDir,  setSortDir]  = useState<'asc' | 'desc'>('desc')
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const vehicles = state.status === 'success' ? state.data : []

  const handleSort = (key: SortKey) => {
    if (key === sortKey) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir(key === 'open_task_count' ? 'desc' : 'asc') }
  }

  const q = search.trim().toLowerCase()

  const filtered = useMemo(() => {
    const activeFilter = FILTERS.find(f => f.key === filter) ?? FILTERS[0]
    return vehicles
      .filter(v => {
        const matchSearch = !q
          || (v.stock_number ?? '').toLowerCase().includes(q)
          || v.vin.toLowerCase().includes(q)
          || (v.display_name ?? '').toLowerCase().includes(q)
        return matchSearch && activeFilter.test(v)
      })
      .sort((a, b) => {
        let av: string | number, bv: string | number
        switch (sortKey) {
          case 'stock_number':           av = a.stock_number ?? '';           bv = b.stock_number ?? '';           break
          case 'make':                   av = a.display_name ?? '';           bv = b.display_name ?? '';           break
          case 'current_dealership_id':  av = a.current_dealership_id ?? '';  bv = b.current_dealership_id ?? '';  break
          case 'open_task_count':        av = a.open_task_count;              bv = b.open_task_count;              break
          default:                       av = 0;                             bv = 0
        }
        const cmp = av < bv ? -1 : av > bv ? 1 : 0
        return sortDir === 'asc' ? cmp : -cmp
      })
  }, [vehicles, q, filter, sortKey, sortDir])

  const filterCounts = useMemo(() =>
    Object.fromEntries(FILTERS.map(f => [f.key, vehicles.filter(f.test).length])) as Record<FilterKey, number>,
  [vehicles])

  const allSelected  = filtered.length > 0 && filtered.every(v => selected.has(v.vin))
  const someSelected = filtered.some(v => selected.has(v.vin))
  const selectedCount = selected.size

  const toggleAll = () => {
    if (allSelected) {
      setSelected(prev => { const n = new Set(prev); filtered.forEach(v => n.delete(v.vin)); return n })
    } else {
      setSelected(prev => { const n = new Set(prev); filtered.forEach(v => n.add(v.vin)); return n })
    }
  }

  const toggleOne = (vin: string) => {
    setSelected(prev => { const n = new Set(prev); n.has(vin) ? n.delete(vin) : n.add(vin); return n })
  }

  const clearSelection = () => setSelected(new Set())

  return (
    <div className="flex-1 flex flex-col overflow-hidden min-h-0">

      {/* Toolbar */}
      <div className="flex-shrink-0 flex items-center gap-3 px-5 py-2.5 bg-white border-b border-slate-200 flex-wrap">
        <div className="relative">
          <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" width="13" height="13" fill="none" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8"/>
            <path d="m16.5 16.5 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Stock, VIN, make, model…"
            className="h-8 w-64 pl-8 pr-7 text-[12px] bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all" />
          {search && (
            <button onClick={() => setSearch('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
            </button>
          )}
        </div>

        <div className="flex items-center gap-1">
          {FILTERS.map(({ key, label }) => {
            const count = filterCounts[key] ?? 0
            if (key !== 'all' && !count) return null
            const active = filter === key
            return (
              <button key={key} onClick={() => setFilter(active && key !== 'all' ? 'all' : key)}
                className={`text-[11px] font-bold px-2.5 py-1 rounded-full border transition-all ${
                  active
                    ? 'bg-slate-800 text-white border-slate-800'
                    : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300 hover:text-slate-700'
                }`}>
                {label} <span className="opacity-50 font-normal">{count}</span>
              </button>
            )
          })}
        </div>

        <div className="flex-1" />

        <span className="text-[11px] text-slate-400 tabular-nums">
          {filtered.length} of {vehicles.length}
        </span>
      </div>

      {selectedCount > 0 && (
        <BulkToolbar count={selectedCount} onClear={clearSelection} />
      )}

      <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
        {state.status === 'loading' && (
          <CenteredMessage>{spinner}<p className="text-[13px] font-medium">Loading vehicles…</p></CenteredMessage>
        )}

        {state.status === 'error' && (
          <CenteredMessage>
            <p className="text-[13px] font-medium text-red-500">
              {isBackendUnavailable(state.error) ? 'The LotSync API is unreachable.' : 'Something went wrong loading vehicles.'}
            </p>
            <p className="text-[11px] text-slate-400">{state.error.message}</p>
          </CenteredMessage>
        )}

        {state.status === 'success' && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center h-48 text-slate-400">
            <svg width="28" height="28" fill="none" viewBox="0 0 24 24" className="mb-2 opacity-30">
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.5"/>
              <path d="m16.5 16.5 4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            <p className="text-[13px] font-medium">{vehicles.length === 0 ? 'No vehicles yet' : 'No vehicles match'}</p>
            {vehicles.length > 0 && (
              <button onClick={() => { setSearch(''); setFilter('all') }}
                className="mt-2 text-[11px] text-blue-600 hover:underline">Clear all filters</button>
            )}
          </div>
        )}

        {state.status === 'success' && filtered.length > 0 && (
          <table className="w-full border-collapse">
            <thead className="sticky top-0 z-10 bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="pl-4 pr-3 py-2.5 w-8">
                  <input type="checkbox"
                    checked={allSelected}
                    ref={el => { if (el) el.indeterminate = someSelected && !allSelected }}
                    onChange={toggleAll}
                    className="w-3.5 h-3.5 rounded border-slate-300 cursor-pointer accent-blue-600" />
                </th>
                <th className="py-2.5 pr-5 text-left w-24">
                  <ColHeader label="Stock #" sortKey="stock_number" current={sortKey} dir={sortDir} onSort={handleSort} />
                </th>
                <th className="py-2.5 pr-5 text-left" style={{ width: '220px' }}>
                  <ColHeader label="Vehicle" sortKey="make" current={sortKey} dir={sortDir} onSort={handleSort} />
                </th>
                <th className="py-2.5 pr-5 text-left" style={{ width: '160px' }}>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">VIN</span>
                </th>
                <th className="py-2.5 pr-5 text-left" style={{ width: '120px' }}>
                  <ColHeader label="Dealership" sortKey="current_dealership_id" current={sortKey} dir={sortDir} onSort={handleSort} />
                </th>
                <th className="py-2.5 pr-5 w-20 text-center">
                  <ColHeader label="Tasks" sortKey="open_task_count" current={sortKey} dir={sortDir} onSort={handleSort} />
                </th>
                <th className="py-2.5 px-5 text-center">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Systems</span>
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-100">
              {filtered.map(v => (
                <VehicleRow
                  key={v.vin} v={v} query={q}
                  selected={selected.has(v.vin)}
                  onToggle={toggleOne}
                  onSelect={onVehicleSelect}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
