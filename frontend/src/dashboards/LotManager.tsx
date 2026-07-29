// Sprint 3 (Frontend Integration): the LeftCol (Inventory Health,
// Connected Systems) and RightCol's Live Activity panel are wired to
// GET /dashboard (DashboardSummaryDTO) -- one fetch for this whole
// screen, per API_CONTRACTS.md's own reading ("its 'Live Activity'...
// panel[is] covered too via the same response's recent_activity").
// CenterCol's "Today's Operations" task board and RightCol's "Team
// Status" / "Suggestions" panels remain mock, deliberately: real Task
// data needs the commitment_standing/execution_status frontend
// correction first (this sprint's own later, dedicated step), Team
// Status has no backend current-assignment concept yet, and
// Suggestions (Recommendations) is this sprint's own next step, not
// this one. See PHASE_3_SPRINT_3_REVIEW.md.
//
// The mockup's 3-tier health breakdown (Fully Verified / Needs
// Attention / Critical, with fabricated counts) and "Morning Sync"
// summary card (Vehicles Processed / Issues Found / Tasks Generated)
// have no backend equivalent -- InventoryHealthDTO is a 2-way split
// (healthy vs. not), and issues_found/tasks_generated aren't part of
// the derived Connected Systems read the API actually serves. Rendered
// honestly (2-tier ring, Morning Sync card dropped) rather than kept
// as fabricated numbers.

import { useState } from 'react'
import { getDashboard } from '../api/dashboard'
import { getRecommendations } from '../api/recommendations'
import { useApi, type ApiState } from '../api/useApi'
import { isBackendUnavailable } from '../api/client'
import type { ActivityDTO, ConnectedSystemStatusDTO, RecommendationDTO } from '../api/types'

// ─── Shared icons ─────────────────────────────────────────────────────────────

const Ic = {
  chevDown: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  chevRight: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="m9 18 6-6-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  check: <svg width="11" height="11" fill="none" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  warn: <svg width="11" height="11" fill="none" viewBox="0 0 24 24"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/><circle cx="12" cy="17" r="0.5" fill="currentColor" stroke="currentColor" strokeWidth="1.2"/></svg>,
  plus: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>,
  ai: <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><path d="M12 2 9.5 9.5 2 12l7.5 2.5L12 22l2.5-7.5L22 12l-7.5-2.5L12 2z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"/></svg>,
  users: <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/><circle cx="9" cy="7" r="4" stroke="currentColor" strokeWidth="1.75"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></svg>,
  activity: <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>,
}

// ─── Data ─────────────────────────────────────────────────────────────────────

type TaskPriority = 'Critical' | 'High' | 'Medium' | 'Low'
type TaskCategory = 'Inventory' | 'Controller' | 'Lot' | 'Dealer Trades'
type TeamStatus = 'Available' | 'Driving' | 'Dealer Trade' | 'Installing' | 'Lunch' | 'Helping Sales'

const priorityMeta: Record<TaskPriority, { bg: string; text: string; border: string }> = {
  Critical: { bg: 'bg-red-50', text: 'text-red-600', border: 'border-red-200' },
  High: { bg: 'bg-orange-50', text: 'text-orange-600', border: 'border-orange-200' },
  Medium: { bg: 'bg-amber-50', text: 'text-amber-600', border: 'border-amber-200' },
  Low: { bg: 'bg-slate-100', text: 'text-slate-500', border: 'border-slate-200' },
}

const statusMeta: Record<TeamStatus, { bg: string; text: string; dot: string }> = {
  Available: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-400' },
  Driving: { bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-400' },
  'Dealer Trade': { bg: 'bg-violet-50', text: 'text-violet-700', dot: 'bg-violet-400' },
  Installing: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-400' },
  Lunch: { bg: 'bg-slate-100', text: 'text-slate-500', dot: 'bg-slate-400' },
  'Helping Sales': { bg: 'bg-indigo-50', text: 'text-indigo-700', dot: 'bg-indigo-400' },
}

const categoryMeta: Record<TaskCategory, { color: string; bg: string; label: string }> = {
  Inventory: { color: 'text-blue-700', bg: 'bg-blue-50', label: 'Inventory' },
  Controller: { color: 'text-violet-700', bg: 'bg-violet-50', label: 'Controller' },
  Lot: { color: 'text-emerald-700', bg: 'bg-emerald-50', label: 'Lot Ops' },
  'Dealer Trades': { color: 'text-orange-700', bg: 'bg-orange-50', label: 'Dealer Trades' },
}

const categories: TaskCategory[] = ['Inventory', 'Controller', 'Lot', 'Dealer Trades']

interface OpCard {
  id: string; title: string; category: TaskCategory; priority: TaskPriority
  eta: string; assigned: string; initials: string; vehicleCount: number
  progress: number; total: number; stock?: string
}

const opCards: OpCard[] = [
  { id: 'i1', title: 'Install RecovR Devices', category: 'Inventory', priority: 'High', eta: '~45 min', assigned: 'M. Torres', initials: 'MT', vehicleCount: 6, progress: 1, total: 6, stock: 'A48291' },
  { id: 'i2', title: 'Install MDD Devices', category: 'Inventory', priority: 'High', eta: '~20 min', assigned: 'D. Okafor', initials: 'DO', vehicleCount: 2, progress: 0, total: 2 },
  { id: 'i3', title: 'Replace Stock Tags', category: 'Inventory', priority: 'Medium', eta: '~30 min', assigned: 'K. Williams', initials: 'KW', vehicleCount: 8, progress: 3, total: 8 },
  { id: 'i4', title: 'Verify Incoming Vehicles', category: 'Inventory', priority: 'High', eta: '~25 min', assigned: 'S. Park', initials: 'SP', vehicleCount: 5, progress: 0, total: 5 },
  { id: 'c1', title: 'Verify Sold Vehicles', category: 'Controller', priority: 'Critical', eta: '~15 min', assigned: 'R. Gutierrez', initials: 'RG', vehicleCount: 3, progress: 1, total: 3 },
  { id: 'c2', title: 'Resolve DMS Exceptions', category: 'Controller', priority: 'High', eta: '~40 min', assigned: 'R. Gutierrez', initials: 'RG', vehicleCount: 4, progress: 0, total: 4 },
  { id: 'c3', title: 'Approve Placeholder Stocks', category: 'Controller', priority: 'Medium', eta: '~10 min', assigned: 'R. Gutierrez', initials: 'RG', vehicleCount: 2, progress: 0, total: 2 },
  { id: 'l1', title: 'Move Vehicles to Staging', category: 'Lot', priority: 'Medium', eta: '~50 min', assigned: 'M. Torres', initials: 'MT', vehicleCount: 6, progress: 2, total: 6 },
  { id: 'l2', title: 'Fuel Vehicles', category: 'Lot', priority: 'Low', eta: '~25 min', assigned: 'K. Williams', initials: 'KW', vehicleCount: 3, progress: 0, total: 3 },
  { id: 'l3', title: 'Wash & Detail', category: 'Lot', priority: 'Low', eta: '~1.5 hrs', assigned: 'D. Okafor', initials: 'DO', vehicleCount: 4, progress: 1, total: 4 },
  { id: 'l4', title: 'Prepare Customer Deliveries', category: 'Lot', priority: 'High', eta: '~1 hr', assigned: 'S. Park', initials: 'SP', vehicleCount: 2, progress: 0, total: 2 },
  { id: 'd1', title: 'Pending Pickup', category: 'Dealer Trades', priority: 'High', eta: 'By 11 AM', assigned: 'M. Torres', initials: 'MT', vehicleCount: 2, progress: 0, total: 2 },
  { id: 'd2', title: 'Awaiting Driver Assignment', category: 'Dealer Trades', priority: 'Critical', eta: 'ASAP', assigned: 'Unassigned', initials: '?', vehicleCount: 1, progress: 0, total: 1 },
  { id: 'd3', title: 'Accepted — In Transit', category: 'Dealer Trades', priority: 'Medium', eta: '~2 hrs', assigned: 'D. Okafor', initials: 'DO', vehicleCount: 3, progress: 1, total: 3 },
]

const teamMembers = [
  { name: 'Marcus Torres', initials: 'MT', color: '#2563EB', status: 'Installing' as TeamStatus, task: 'Installing RecovR', vehicle: 'A48291', eta: '22 min' },
  { name: 'Keisha Williams', initials: 'KW', color: '#7C3AED', status: 'Driving' as TeamStatus, task: 'Moving vehicles', vehicle: 'F38102', eta: '8 min' },
  { name: 'David Okafor', initials: 'DO', color: '#0891B2', status: 'Dealer Trade' as TeamStatus, task: 'Dealer trade run', vehicle: 'G10923', eta: '45 min' },
  { name: 'Sara Park', initials: 'SP', color: '#059669', status: 'Available' as TeamStatus, task: 'Ready for task', vehicle: '', eta: '' },
  { name: 'R. Gutierrez', initials: 'RG', color: '#D97706', status: 'Helping Sales' as TeamStatus, task: 'Assisting showroom', vehicle: 'C84711', eta: '10 min' },
  { name: 'T. Mabunda', initials: 'TM', color: '#64748B', status: 'Lunch' as TeamStatus, task: 'On lunch break', vehicle: '', eta: '25 min' },
]

// ─── Health Ring ──────────────────────────────────────────────────────────────

// Two-tier (healthy vs. needs attention) -- InventoryHealthDTO has no
// "Critical" tier of its own; a fabricated 3-way split isn't rendered.
function HealthRing({ healthy, total, percentage }: { healthy: number; total: number; percentage: number | null }) {
  const R = 52, C = 2 * Math.PI * R
  const score = percentage ?? 0
  const needsAttention = total - healthy
  return (
    <div className="flex flex-col items-center gap-3">
      <svg width="128" height="128" viewBox="0 0 128 128">
        <circle cx="64" cy="64" r={R} fill="none" stroke="#E2E8F0" strokeWidth="10" />
        <circle cx="64" cy="64" r={R} fill="none" stroke="#16A34A" strokeWidth="10"
          strokeDasharray={`${(score / 100) * C} ${C - (score / 100) * C}`}
          strokeDashoffset={C / 4} strokeLinecap="round" transform="rotate(-90 64 64)"
          style={{ filter: 'drop-shadow(0 0 6px #16A34A40)' }} />
        <text x="64" y="58" textAnchor="middle" fontFamily="'Plus Jakarta Sans',sans-serif" fontSize="26" fontWeight="800" fill="#0F172A">
          {percentage === null ? '—' : `${Math.round(score)}%`}
        </text>
        <text x="64" y="76" textAnchor="middle" fontFamily="'Plus Jakarta Sans',sans-serif" fontSize="11" fontWeight="600" fill="#16A34A">Healthy</text>
      </svg>
      <div className="w-full space-y-2">
        {[
          { label: 'Healthy', pct: total ? (healthy / total) * 100 : 0, color: '#16A34A', count: healthy },
          { label: 'Needs Attention', pct: total ? (needsAttention / total) * 100 : 0, color: '#D97706', count: needsAttention },
        ].map(r => (
          <div key={r.label} className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: r.color }} />
            <span className="text-[11px] text-slate-500 flex-1 truncate">{r.label}</span>
            <div className="w-16 h-1 bg-slate-100 rounded-full overflow-hidden">
              <div className="h-full rounded-full" style={{ width: `${r.pct}%`, backgroundColor: r.color }} />
            </div>
            <span className="text-[11px] font-semibold text-slate-700 tabular-nums w-8 text-right">{r.count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function StockPill({ stock, label, onSelect }: { stock: string; label?: string; onSelect: (s: string) => void }) {
  return (
    <button onClick={() => onSelect(stock)} className="font-mono text-[11px] font-bold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-1.5 py-0.5 rounded transition-colors">
      {label ?? stock}
    </button>
  )
}

// ─── Left Column ──────────────────────────────────────────────────────────────

function formatSyncTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

function LeftCol({ connectedSystems, healthy, total, percentage }: {
  connectedSystems: Record<string, ConnectedSystemStatusDTO>
  healthy: number; total: number; percentage: number | null
}) {
  const systemEntries = Object.entries(connectedSystems)

  return (
    <div className="w-64 flex-shrink-0 flex flex-col gap-4 overflow-y-auto pb-6" style={{ scrollbarWidth: 'none' }}>
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <span className="text-[12px] font-bold text-slate-700 uppercase tracking-wider">Inventory Health</span>
          <span className="text-[10px] text-slate-400">{total.toLocaleString()} vehicles</span>
        </div>
        <HealthRing healthy={healthy} total={total} percentage={percentage} />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="text-[12px] font-bold text-slate-700 uppercase tracking-wider mb-3">Connected Systems</div>
        <div className="space-y-2">
          {systemEntries.length === 0 && <p className="text-[11px] text-slate-400">No sync history yet.</p>}
          {systemEntries.map(([name, sys]) => (
            <div key={name} className="rounded-lg border border-slate-100 p-3 hover:border-slate-200 transition-colors">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full ${sys.status === 'complete' ? 'bg-emerald-400' : sys.status === 'failed' ? 'bg-red-500' : 'bg-amber-400'}`} />
                  <span className="text-[13px] font-bold text-slate-900 capitalize">{name}</span>
                </div>
                {sys.status === 'complete'
                  ? <span className="text-emerald-500">{Ic.check}</span>
                  : <span className="text-[10px] font-semibold text-amber-600 capitalize">{Ic.warn} {sys.status}</span>}
              </div>
              <div className="flex justify-between">
                <span className="text-[10px] text-slate-400">{(sys.records_processed ?? 0).toLocaleString()} records</span>
                <span className="text-[10px] font-mono text-slate-400">{formatSyncTime(sys.completed_at ?? sys.started_at)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Center Column ────────────────────────────────────────────────────────────

function CenterCol({ onVehicleSelect }: { onVehicleSelect: (s: string) => void }) {
  const [filter, setFilter] = useState<TaskCategory | 'All'>('All')
  const [collapsed, setCollapsed] = useState<Partial<Record<TaskCategory, boolean>>>({})
  const [started, setStarted] = useState<Set<string>>(new Set())

  const vis = filter === 'All' ? categories : [filter]

  return (
    <div className="flex-1 flex flex-col gap-4 overflow-hidden min-w-0">
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h2 className="text-[18px] font-bold text-slate-900 tracking-tight">Today's Operations</h2>
          <p className="text-[12px] text-slate-400 mt-0.5">{opCards.length} tasks · <span className="text-red-500 font-semibold">2 critical</span> · 3 in progress</p>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
            {(['All', ...categories] as (TaskCategory | 'All')[]).map(cat => (
              <button key={cat} onClick={() => setFilter(cat)}
                className={`text-[11px] font-semibold px-2.5 py-1 rounded-md transition-all ${filter === cat ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
                {cat === 'All' ? 'All' : categoryMeta[cat].label}
              </button>
            ))}
          </div>
          <button className="flex items-center gap-1.5 text-[11px] font-bold text-blue-600 px-3 py-1.5 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg transition-colors">
            {Ic.plus} New Task
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-5 pb-6 pr-1" style={{ scrollbarWidth: 'thin' }}>
        {vis.map(cat => {
          const cards = opCards.filter(c => c.category === cat)
          const isCollapsed = collapsed[cat]
          const cm = categoryMeta[cat]
          return (
            <div key={cat}>
              <button className="w-full flex items-center gap-2 mb-2.5 group"
                onClick={() => setCollapsed(p => ({ ...p, [cat]: !p[cat] }))}>
                <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-md ${cm.bg} ${cm.color}`}>{cm.label}</span>
                <span className="text-[12px] text-slate-400">{cards.length} tasks</span>
                {cards.filter(c => c.priority === 'Critical').length > 0 && (
                  <span className="text-[10px] font-bold text-red-500">· {cards.filter(c => c.priority === 'Critical').length} critical</span>
                )}
                <div className="flex-1 h-px bg-slate-100" />
                <span className="text-slate-300 group-hover:text-slate-400">{isCollapsed ? Ic.chevRight : Ic.chevDown}</span>
              </button>

              {!isCollapsed && (
                <div className="grid grid-cols-2 gap-3">
                  {cards.map(card => {
                    const prog = started.has(card.id) ? Math.min(card.progress + 1, card.total) : card.progress
                    const pct = Math.round((prog / card.total) * 100)
                    const pm = priorityMeta[card.priority]
                    const inProg = prog > 0 && prog < card.total
                    const unassigned = card.assigned === 'Unassigned'
                    return (
                      <div key={card.id} className={`bg-white rounded-xl border p-4 hover:shadow-md hover:-translate-y-px transition-all duration-200 cursor-default group ${card.priority === 'Critical' ? 'border-red-200' : 'border-slate-200'}`}>
                        <div className="flex items-start justify-between gap-2 mb-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                              <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${pm.bg} ${pm.text} ${pm.border}`}>
                                {card.priority === 'Critical' && '!'}{card.priority}
                              </span>
                              {inProg && <span className="text-[10px] font-semibold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-100">In Progress</span>}
                              {card.stock && <StockPill stock={card.stock} onSelect={onVehicleSelect} />}
                            </div>
                            <h3 className="text-[14px] font-bold text-slate-900 leading-tight">{card.title}</h3>
                          </div>
                          <div className="w-8 h-8 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-center text-[13px] font-bold text-slate-700 flex-shrink-0">{card.vehicleCount}</div>
                        </div>
                        <div className="mb-3">
                          <div className="flex justify-between mb-1">
                            <span className="text-[10px] text-slate-400">{prog} of {card.total} complete</span>
                            <span className="text-[10px] font-semibold text-slate-500">{pct}%</span>
                          </div>
                          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full rounded-full transition-all duration-500"
                              style={{ width: `${pct}%`, backgroundColor: pct === 100 ? '#16A34A' : pct > 0 ? '#2563EB' : '#94A3B8' }} />
                          </div>
                        </div>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-white flex-shrink-0"
                              style={{ backgroundColor: unassigned ? '#DC2626' : '#64748B' }}>{card.initials}</div>
                            <div>
                              <div className={`text-[11px] font-semibold ${unassigned ? 'text-red-600' : 'text-slate-700'}`}>{card.assigned}</div>
                              <div className="text-[10px] text-slate-400">{card.eta}</div>
                            </div>
                          </div>
                          <button onClick={() => setStarted(p => new Set(p).add(card.id))}
                            className={`text-[11px] font-bold px-3 py-1.5 rounded-lg border transition-all ${unassigned ? 'bg-red-600 text-white border-red-600 hover:bg-red-700' : inProg ? 'bg-blue-600 text-white border-blue-600 hover:bg-blue-700' : 'bg-white text-slate-700 border-slate-200 hover:border-blue-300 hover:text-blue-600'}`}>
                            {unassigned ? 'Assign' : inProg ? 'Continue' : 'Start'}
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── Right Column ─────────────────────────────────────────────────────────────

function formatActivityTime(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

function RightCol({ onVehicleSelect, recentActivity, recommendations }: {
  onVehicleSelect: (s: string) => void
  recentActivity: ActivityDTO[]
  recommendations: ApiState<RecommendationDTO[]>
}) {
  return (
    <div className="w-72 flex-shrink-0 flex flex-col gap-4 overflow-y-auto pb-6" style={{ scrollbarWidth: 'none' }}>
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">{Ic.users}</span>
            <span className="text-[12px] font-bold text-slate-700 uppercase tracking-wider">Team Status</span>
          </div>
          <span className="text-[10px] text-emerald-600 font-semibold bg-emerald-50 border border-emerald-100 px-1.5 py-0.5 rounded-full">
            {teamMembers.filter(t => t.status === 'Available').length} available
          </span>
        </div>
        <div className="space-y-1.5">
          {teamMembers.map(m => {
            const sm = statusMeta[m.status]
            return (
              <div key={m.name} className="flex items-center gap-2.5 p-2.5 rounded-lg hover:bg-slate-50 transition-colors border border-transparent hover:border-slate-100">
                <div className="relative flex-shrink-0">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold text-white" style={{ backgroundColor: m.color }}>{m.initials}</div>
                  <span className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-white ${sm.dot}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-[12px] font-bold text-slate-900 truncate">{m.name}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md flex-shrink-0 ${sm.bg} ${sm.text}`}>{m.status}</span>
                  </div>
                  <div className="text-[11px] text-slate-400 truncate">{m.task}</div>
                  {m.vehicle && (
                    <button onClick={() => onVehicleSelect(m.vehicle)} className="text-[10px] font-mono font-bold text-blue-600 hover:underline">Stock {m.vehicle}</button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex items-center gap-1.5 mb-3">
          <span className="text-slate-400">{Ic.activity}</span>
          <span className="text-[12px] font-bold text-slate-700 uppercase tracking-wider">Live Activity</span>
          <span className="ml-auto text-[10px] text-emerald-600 font-semibold flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Live</span>
        </div>
        <div className="space-y-0">
          {recentActivity.length === 0 && <p className="text-[11px] text-slate-400 py-2">No recent activity.</p>}
          {recentActivity.map((item, i) => (
            <div key={item.event_id} className="flex gap-2.5 py-2 border-b border-slate-50 last:border-0">
              <div className="flex flex-col items-center flex-shrink-0">
                <span className="w-1.5 h-1.5 rounded-full mt-1 bg-blue-400" />
                {i < recentActivity.length - 1 && <div className="w-px flex-1 bg-slate-100 mt-0.5" />}
              </div>
              <div className="flex-1 min-w-0 pb-1">
                <div className="text-[10px] font-mono text-slate-400 mb-0.5">{formatActivityTime(item.observed_at)}</div>
                <div className="text-[12px] text-slate-700">
                  {item.summary ?? item.event_type}
                  {item.vehicle?.stock_number && (
                    <span className="ml-1.5"><StockPill stock={item.vehicle.vin} label={item.vehicle.stock_number} onSelect={onVehicleSelect} /></span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex items-center gap-1.5 mb-3">
          <span className="text-violet-500">{Ic.ai}</span>
          <span className="text-[12px] font-bold text-slate-700 uppercase tracking-wider">Suggestions</span>
          <span className="ml-auto text-[10px] text-violet-600 font-semibold bg-violet-50 border border-violet-100 px-1.5 py-0.5 rounded-full">AI</span>
        </div>
        <div className="space-y-2">
          {recommendations.status === 'loading' && <p className="text-[11px] text-slate-400">Loading…</p>}
          {recommendations.status === 'error' && (
            <p className="text-[11px] text-red-500">
              {isBackendUnavailable(recommendations.error) ? 'API unreachable.' : 'Failed to load suggestions.'}
            </p>
          )}
          {recommendations.status === 'success' && recommendations.data.length === 0 && (
            <p className="text-[11px] text-slate-400">No open recommendations.</p>
          )}
          {recommendations.status === 'success' && recommendations.data.map(rec => (
            <div key={rec.recommendation_id} className="rounded-lg border border-slate-100 p-3 hover:border-violet-200 hover:bg-violet-50/30 transition-all group">
              <div className="flex items-start gap-2 mb-1.5">
                <span className={`mt-1 flex-shrink-0 w-1.5 h-1.5 rounded-full ${rec.severity === 'Critical' || rec.severity === 'High' ? 'bg-red-400' : 'bg-amber-400'}`} />
                <p className="text-[12px] text-slate-700 leading-snug">{rec.title ?? rec.rule_source}</p>
              </div>
              {rec.vehicle?.stock_number && (
                <div className="ml-3.5"><StockPill stock={rec.vehicle.vin} label={rec.vehicle.stock_number} onSelect={onVehicleSelect} /></div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Lot Manager Dashboard ────────────────────────────────────────────────────

export default function LotManagerDashboard({ onVehicleSelect }: { onVehicleSelect: (s: string) => void }) {
  const state = useApi(() => getDashboard(), [])
  const recommendations = useApi(() => getRecommendations({ status: 'open' }), [])

  if (state.status === 'loading') {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-[13px] font-medium text-slate-400">Loading dashboard…</p>
      </div>
    )
  }

  if (state.status === 'error') {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-2 text-slate-400">
          <p className="text-[13px] font-medium text-red-500">
            {isBackendUnavailable(state.error) ? 'The LotSync API is unreachable.' : 'Something went wrong loading the dashboard.'}
          </p>
          <p className="text-[11px] text-slate-400">{state.error.message}</p>
        </div>
      </div>
    )
  }

  const { connected_systems, inventory_health, recent_activity } = state.data

  return (
    <div className="flex-1 flex gap-5 px-5 pt-5 overflow-hidden min-h-0">
      <LeftCol
        connectedSystems={connected_systems}
        healthy={inventory_health.healthy_vehicles}
        total={inventory_health.total_vehicles}
        percentage={inventory_health.health_percentage}
      />
      <CenterCol onVehicleSelect={onVehicleSelect} />
      <RightCol onVehicleSelect={onVehicleSelect} recentActivity={recent_activity} recommendations={recommendations} />
    </div>
  )
}
