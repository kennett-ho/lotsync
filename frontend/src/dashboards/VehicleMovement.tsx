// VehicleMovement.tsx — Lot movement dispatch board

import { useState, useMemo } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

type MoveStatus   = 'requested' | 'assigned' | 'accepted' | 'completed' | 'cancelled'
type MoveType     = 'lot-move' | 'service-pull' | 'showroom' | 'staging' | 'delivery' | 'dealer-trade'
type MovePriority = 'urgent' | 'normal' | 'low'

interface MoveVehicle {
  stock: string; year: number; make: string; model: string; color: string
  fromZone: string; toZone: string
}

interface VehicleMovement {
  id: string; type: MoveType; label: string
  status: MoveStatus; priority: MovePriority
  requestedBy: string; requestedByTitle: string; requestedAt: string
  assignedTo?: string
  dueLabel?: string; dueMinutes?: number | null
  vehicles: MoveVehicle[]
  notes?: string
  updatedLabel: string
  timeline: { label: string; sublabel?: string; done: boolean; active?: boolean }[]
}

// ─── Data ─────────────────────────────────────────────────────────────────────

const MOVEMENTS: VehicleMovement[] = [
  {
    id: 'm1', type: 'dealer-trade', label: 'Dealer Trade Pickup',
    status: 'assigned', priority: 'urgent',
    requestedBy: 'Rosa Pereira', requestedByTitle: 'Tower Manager', requestedAt: 'Today · 8:42 AM',
    assignedTo: 'Jordan Davis', dueLabel: 'ASAP', dueMinutes: -1,
    vehicles: [
      { stock: 'H72840', year: 2023, make: 'Subaru', model: 'Outback', color: 'Crystal White', fromZone: 'Kia Front Lot', toZone: 'Offsite — Sunrise Honda' },
      { stock: 'G19283', year: 2022, make: 'Toyota', model: 'RAV4', color: 'Magnetic Gray', fromZone: 'Toyota Row', toZone: 'Offsite — Sunrise Honda' },
      { stock: 'B39281', year: 2024, make: 'Honda', model: 'CR-V', color: 'Sonic Gray Pearl', fromZone: 'Honda Row', toZone: 'Offsite — Sunrise Honda' },
    ],
    notes: 'Confirm with Rosa before departure. Dealer plates in key cabinet.',
    updatedLabel: '2 min ago',
    timeline: [
      { label: 'Requested', sublabel: 'Rosa Pereira · 8:42 AM', done: true },
      { label: 'Assigned', sublabel: 'Jordan Davis', done: true },
      { label: 'Accepted', sublabel: 'Pending', done: false, active: true },
      { label: 'Completed', sublabel: '', done: false },
    ],
  },
  {
    id: 'm2', type: 'service-pull', label: 'Service Pull',
    status: 'accepted', priority: 'urgent',
    requestedBy: 'Lisa Martinez', requestedByTitle: 'Service Advisor', requestedAt: 'Received 17 min ago',
    assignedTo: 'Marcus Torres', dueLabel: 'Due in 30 min', dueMinutes: 30,
    vehicles: [
      { stock: 'E51388', year: 2023, make: 'BMW', model: '5 Series', color: 'Mineral White', fromZone: 'Premium Row', toZone: 'Service Bay 1' },
    ],
    updatedLabel: '5 min ago',
    timeline: [
      { label: 'Requested', sublabel: 'Lisa Martinez · 8:55 AM', done: true },
      { label: 'Assigned', sublabel: 'Marcus Torres', done: true },
      { label: 'Accepted', sublabel: 'Marcus Torres', done: true },
      { label: 'Completed', sublabel: 'In progress', done: false, active: true },
    ],
  },
  {
    id: 'm3', type: 'showroom', label: 'Showroom Staging',
    status: 'requested', priority: 'normal',
    requestedBy: 'Ben Wheeler', requestedByTitle: 'Sales Manager', requestedAt: 'Today · 9:41 AM',
    dueLabel: 'Due 12:30 PM', dueMinutes: 150,
    vehicles: [
      { stock: 'A48291', year: 2023, make: 'Honda', model: 'Accord', color: 'Sonic Gray Pearl', fromZone: 'Kia Front Lot', toZone: 'Showroom Floor' },
    ],
    updatedLabel: '12 min ago',
    timeline: [
      { label: 'Requested', sublabel: 'Ben Wheeler · 9:41 AM', done: true },
      { label: 'Assigned', sublabel: 'Pending', done: false, active: true },
      { label: 'Accepted', sublabel: '', done: false },
      { label: 'Completed', sublabel: '', done: false },
    ],
  },
  {
    id: 'm4', type: 'lot-move', label: 'Frontline Rotation',
    status: 'requested', priority: 'normal',
    requestedBy: 'Jordan Davis', requestedByTitle: 'Lot Manager', requestedAt: 'Today · 9:15 AM',
    dueLabel: 'Due 3:00 PM', dueMinutes: 270,
    vehicles: [
      { stock: 'D72044', year: 2024, make: 'Kia', model: 'Telluride', color: 'Everest White', fromZone: 'Kia Back Lot', toZone: 'Kia Frontline' },
      { stock: 'H64509', year: 2023, make: 'Mazda', model: 'CX-5', color: 'Platinum Quartz', fromZone: 'Mazda Row', toZone: 'Mazda Frontline' },
    ],
    updatedLabel: '18 min ago',
    timeline: [
      { label: 'Requested', sublabel: 'Jordan Davis · 9:15 AM', done: true },
      { label: 'Assigned', sublabel: 'Pending', done: false, active: true },
      { label: 'Accepted', sublabel: '', done: false },
      { label: 'Completed', sublabel: '', done: false },
    ],
  },
  {
    id: 'm5', type: 'delivery', label: 'Customer Delivery',
    status: 'assigned', priority: 'normal',
    requestedBy: 'Lisa Martinez', requestedByTitle: 'Service Advisor', requestedAt: 'Today · 8:55 AM',
    assignedTo: 'Marcus Torres', dueLabel: 'Due 1:45 PM', dueMinutes: 210,
    vehicles: [
      { stock: 'B93021', year: 2024, make: 'Toyota', model: 'Camry', color: 'Midnight Black', fromZone: 'Toyota Front Row', toZone: 'Delivery Bay 2' },
    ],
    updatedLabel: '30 min ago',
    timeline: [
      { label: 'Requested', sublabel: 'Lisa Martinez · 8:55 AM', done: true },
      { label: 'Assigned', sublabel: 'Marcus Torres', done: true },
      { label: 'Accepted', sublabel: 'In progress', done: false, active: true },
      { label: 'Completed', sublabel: '', done: false },
    ],
  },
  {
    id: 'm6', type: 'staging', label: 'Fuel & Stage Trucks',
    status: 'accepted', priority: 'normal',
    requestedBy: 'Jordan Davis', requestedByTitle: 'Lot Manager', requestedAt: 'Today · 8:22 AM',
    assignedTo: 'Marcus Torres', dueLabel: 'Today', dueMinutes: null,
    vehicles: [
      { stock: 'F29917', year: 2022, make: 'Chevrolet', model: 'Silverado', color: 'Black', fromZone: 'Truck Row A', toZone: 'Delivery Ready Bay' },
      { stock: 'C84711', year: 2022, make: 'Ford', model: 'F-150', color: 'Oxford White', fromZone: 'Truck Row B', toZone: 'Delivery Ready Bay' },
    ],
    updatedLabel: '45 min ago',
    timeline: [
      { label: 'Requested', sublabel: 'Jordan Davis · 8:22 AM', done: true },
      { label: 'Assigned', sublabel: 'Marcus Torres', done: true },
      { label: 'Accepted', sublabel: 'Marcus Torres', done: true },
      { label: 'Completed', sublabel: 'In progress', done: false, active: true },
    ],
  },
  {
    id: 'm7', type: 'lot-move', label: 'Zone Rotation',
    status: 'completed', priority: 'normal',
    requestedBy: 'Jordan Davis', requestedByTitle: 'Lot Manager', requestedAt: 'Yesterday · 4:00 PM',
    assignedTo: 'K. Williams', dueLabel: 'Completed',
    vehicles: [
      { stock: 'G11203', year: 2024, make: 'Hyundai', model: 'Tucson', color: 'Silver', fromZone: 'Back Lot', toZone: 'Hyundai Row' },
    ],
    updatedLabel: 'Yesterday',
    timeline: [
      { label: 'Requested', sublabel: 'Jordan Davis · 4:00 PM', done: true },
      { label: 'Assigned', sublabel: 'K. Williams', done: true },
      { label: 'Accepted', sublabel: 'K. Williams', done: true },
      { label: 'Completed', sublabel: 'Yesterday 5:12 PM', done: true },
    ],
  },
]

// ─── Config ───────────────────────────────────────────────────────────────────

const statusCfg: Record<MoveStatus, { label: string; dot: string; text: string; bg: string }> = {
  'requested': { label: 'Requested', dot: 'bg-blue-400',    text: 'text-blue-700',    bg: 'bg-blue-50'    },
  'assigned':  { label: 'Assigned',  dot: 'bg-amber-400',   text: 'text-amber-700',   bg: 'bg-amber-50'   },
  'accepted':  { label: 'Accepted',  dot: 'bg-violet-400',  text: 'text-violet-700',  bg: 'bg-violet-50'  },
  'completed': { label: 'Completed', dot: 'bg-emerald-400', text: 'text-emerald-700', bg: 'bg-emerald-50' },
  'cancelled': { label: 'Cancelled', dot: 'bg-slate-300',   text: 'text-slate-400',   bg: 'bg-slate-50'   },
}

const priorityCfg: Record<MovePriority, { label: string; cls: string }> = {
  urgent: { label: 'Urgent', cls: 'bg-red-100 text-red-700 border border-red-200'       },
  normal: { label: 'Normal', cls: 'bg-slate-100 text-slate-500 border border-slate-200' },
  low:    { label: 'Low',    cls: 'bg-slate-50 text-slate-400 border border-slate-200'  },
}

const typeCfg: Record<MoveType, { label: string; color: string; icon: JSX.Element }> = {
  'dealer-trade': {
    label: 'Dealer Trade', color: 'text-orange-500',
    icon: (
      <svg width="12" height="12" fill="none" viewBox="0 0 24 24">
        <path d="M8 7H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/>
        <path d="M15 3H9l-1 4h8l-1-4Z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"/>
        <path d="M9 14l2 2 4-4" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
  },
  'service-pull': {
    label: 'Service Pull', color: 'text-slate-500',
    icon: (
      <svg width="12" height="12" fill="none" viewBox="0 0 24 24">
        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76Z" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
  },
  'showroom': {
    label: 'Showroom', color: 'text-purple-500',
    icon: (
      <svg width="12" height="12" fill="none" viewBox="0 0 24 24">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9Z" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M9 22V12h6v10" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
  },
  'staging': {
    label: 'Staging', color: 'text-blue-500',
    icon: (
      <svg width="12" height="12" fill="none" viewBox="0 0 24 24">
        <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1.75"/>
        <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1.75"/>
        <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1.75"/>
        <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1.75"/>
      </svg>
    ),
  },
  'delivery': {
    label: 'Delivery', color: 'text-emerald-500',
    icon: (
      <svg width="12" height="12" fill="none" viewBox="0 0 24 24">
        <path d="M5 17H3a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11a2 2 0 0 1 2 2v3" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
        <rect x="9" y="11" width="14" height="10" rx="2" stroke="currentColor" strokeWidth="1.75"/>
        <circle cx="12" cy="21" r="1" fill="currentColor"/>
        <circle cx="20" cy="21" r="1" fill="currentColor"/>
      </svg>
    ),
  },
  'lot-move': {
    label: 'Lot Move', color: 'text-slate-400',
    icon: (
      <svg width="12" height="12" fill="none" viewBox="0 0 24 24">
        <path d="M5 12H19M13 6l6 6-6 6" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
  },
}

const VIEW_FILTERS: { id: MoveStatus | 'all'; label: string }[] = [
  { id: 'all',       label: 'All Movements' },
  { id: 'requested', label: 'Requested'     },
  { id: 'assigned',  label: 'Assigned'      },
  { id: 'accepted',  label: 'Accepted'      },
  { id: 'completed', label: 'Completed'     },
  { id: 'cancelled', label: 'Cancelled'     },
]

// ─── Sub-components ───────────────────────────────────────────────────────────

function DueTag({ min, label }: { min?: number | null; label?: string }) {
  if (!label) return null
  const cls =
    min === -1             ? 'text-red-600 font-bold' :
    min != null && min <= 60  ? 'text-orange-600 font-bold' :
    min != null && min <= 180 ? 'text-amber-600 font-semibold' :
    label === 'Completed'  ? 'text-emerald-600 font-semibold' :
    'text-slate-500'
  return <span className={`text-[10px] ${cls} flex-shrink-0`}>{label}</span>
}

function Initials({ name }: { name: string }) {
  const parts = name.trim().split(' ')
  const ini = parts.length >= 2 ? parts[0][0] + parts[parts.length - 1][0] : parts[0].slice(0, 2)
  return (
    <span className="w-7 h-7 rounded-full bg-slate-200 text-slate-600 text-[10px] font-bold flex items-center justify-center flex-shrink-0 uppercase">
      {ini}
    </span>
  )
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function Sidebar({
  view, onView, movements,
}: {
  view: MoveStatus | 'all'
  onView: (v: MoveStatus | 'all') => void
  movements: VehicleMovement[]
}) {
  const count = (v: MoveStatus | 'all') =>
    v === 'all' ? movements.length : movements.filter(m => m.status === v).length

  return (
    <aside className="flex-shrink-0 w-44 bg-white border-r border-slate-200 flex flex-col py-3" style={{ scrollbarWidth: 'none' }}>
      <div className="text-[9px] font-bold uppercase tracking-widest text-slate-400 px-3 pb-1">Views</div>
      <div className="px-2 space-y-0.5 flex-1">
        {VIEW_FILTERS.map(vf => {
          const c = count(vf.id); const on = view === vf.id
          return (
            <button key={vf.id} onClick={() => onView(vf.id)}
              className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all ${on ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}>
              {vf.label}
              {c > 0 && (
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${on ? 'bg-white/20' : 'bg-slate-100 text-slate-500'}`}>
                  {c}
                </span>
              )}
            </button>
          )
        })}
      </div>
    </aside>
  )
}

// ─── Movement list row ────────────────────────────────────────────────────────

function MovementRow({
  m, selected, onSelect,
}: {
  m: VehicleMovement; selected: boolean; onSelect: () => void
}) {
  const tc = typeCfg[m.type]
  const firstVehicle = m.vehicles[0]

  return (
    <button onClick={onSelect}
      className={`w-full text-left px-3 py-2.5 border-b border-slate-100 transition-all ${
        m.priority === 'urgent' ? 'border-l-2 border-l-red-400' : ''
      } ${selected ? 'bg-blue-50' : 'hover:bg-slate-50'}`}>
      {/* Row 1: type icon + label + due tag */}
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className={tc.color}>{tc.icon}</span>
          <span className={`text-[12.5px] font-bold truncate ${selected ? 'text-blue-700' : 'text-slate-900'}`}>{m.label}</span>
        </div>
        <DueTag min={m.dueMinutes} label={m.dueLabel} />
      </div>
      {/* Row 2: requestedBy + assignedTo + vehicle count */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[10px] text-slate-500 truncate max-w-[80px]">{m.requestedBy}</span>
          <span className="text-slate-300 text-[10px]">·</span>
          {m.assignedTo
            ? <span className="text-[10px] text-slate-500 truncate max-w-[70px]">{m.assignedTo}</span>
            : <span className="text-[10px] text-amber-600 font-semibold">Unassigned</span>}
        </div>
        <span className="text-[9px] font-bold bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded-full flex-shrink-0">
          {m.vehicles.length} veh
        </span>
      </div>
      {/* Row 3: fromZone → toZone */}
      {firstVehicle && (
        <div className="flex items-center gap-1 text-[10px] text-slate-400">
          <span className="truncate max-w-[80px]">{firstVehicle.fromZone}</span>
          <svg width="10" height="10" fill="none" viewBox="0 0 24 24" className="flex-shrink-0 text-slate-300">
            <path d="M5 12H19M13 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="truncate max-w-[80px]">{firstVehicle.toZone}</span>
        </div>
      )}
    </button>
  )
}

// ─── Movement detail ──────────────────────────────────────────────────────────

function MovementDetail({
  m, onStatusChange,
}: {
  m: VehicleMovement
  onStatusChange: (id: string, s: MoveStatus) => void
}) {
  const [vehicleExpanded, setVehicleExpanded] = useState(false)
  const sc = statusCfg[m.status]
  const pc = priorityCfg[m.priority]
  const tc = typeCfg[m.type]

  const shownVehicles = vehicleExpanded ? m.vehicles : m.vehicles.slice(0, 3)
  const hiddenCount = m.vehicles.length - 3

  function ActionBar() {
    if (m.status === 'requested') return (
      <div className="flex items-center gap-2">
        <button onClick={() => onStatusChange(m.id, 'assigned')}
          className="text-[12px] font-bold px-4 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          Assign
        </button>
        <button onClick={() => onStatusChange(m.id, 'cancelled')}
          className="text-[12px] text-slate-400 hover:text-red-600 transition-colors px-2">
          Cancel
        </button>
      </div>
    )
    if (m.status === 'assigned') return (
      <div className="flex items-center gap-2">
        <button onClick={() => onStatusChange(m.id, 'accepted')}
          className="text-[12px] font-bold px-4 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          Mark Accepted
        </button>
        <button className="text-[12px] font-semibold px-4 py-1.5 bg-white text-slate-700 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors">
          Reassign
        </button>
        <button onClick={() => onStatusChange(m.id, 'cancelled')}
          className="text-[12px] text-slate-400 hover:text-red-600 transition-colors px-2">
          Cancel
        </button>
      </div>
    )
    if (m.status === 'accepted') return (
      <div className="flex items-center gap-2">
        <button onClick={() => onStatusChange(m.id, 'completed')}
          className="text-[12px] font-bold px-4 py-1.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors">
          Mark Completed
        </button>
        <button className="text-[12px] font-semibold px-4 py-1.5 bg-white text-slate-700 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors">
          Reassign
        </button>
      </div>
    )
    if (m.status === 'completed') return (
      <span className="text-[12px] text-emerald-600 font-semibold flex items-center gap-1.5">
        <svg width="13" height="13" fill="none" viewBox="0 0 24 24">
          <path d="M20 6 9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
        </svg>
        Completed
      </span>
    )
    return null
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden min-h-0 bg-slate-50">
      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b border-slate-200 px-6 pt-4 pb-3">
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <span className={tc.color}>{tc.icon}</span>
              <h2 className="text-[17px] font-bold text-slate-900">{m.label}</h2>
              {m.priority === 'urgent' && (
                <span className={`text-[9px] font-bold px-2 py-0.5 rounded ${pc.cls}`}>URGENT</span>
              )}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`w-1.5 h-1.5 rounded-full ${sc.dot}`} />
              <span className={`text-[11px] font-semibold ${sc.text}`}>{sc.label}</span>
              {m.dueLabel && (
                <>
                  <span className="text-[10px] text-slate-400">·</span>
                  <DueTag min={m.dueMinutes} label={m.dueLabel} />
                </>
              )}
              <span className="text-[10px] text-slate-400">· {m.requestedAt}</span>
            </div>
          </div>
        </div>
        <ActionBar />
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3" style={{ scrollbarWidth: 'thin' }}>

        {/* Movement Info card */}
        <div className="bg-white border border-slate-100 rounded-2xl overflow-hidden">
          {/* Requested by */}
          <div className="px-5 py-4 border-b border-slate-100">
            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-2">Requested By</div>
            <div className="flex items-center gap-2.5">
              <Initials name={m.requestedBy} />
              <div>
                <div className="text-[13px] font-semibold text-slate-900">{m.requestedBy}</div>
                <div className="text-[10px] text-slate-400">{m.requestedByTitle}</div>
              </div>
            </div>
          </div>
          {/* Due */}
          {m.dueLabel && (
            <div className="px-5 py-3 border-b border-slate-100">
              <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Due</div>
              <div className="flex items-center gap-1.5">
                {m.priority === 'urgent' && m.dueMinutes === -1 && (
                  <svg width="12" height="12" fill="none" viewBox="0 0 24 24" className="text-red-500">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.75"/>
                    <path d="M12 8v4M12 16h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                )}
                <DueTag min={m.dueMinutes} label={m.dueLabel} />
              </div>
            </div>
          )}
          {/* Assigned to */}
          <div className="px-5 py-3 flex items-center justify-between">
            <div>
              <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Assigned To</div>
              <div className={`text-[13px] font-semibold ${m.assignedTo ? 'text-slate-900' : 'text-amber-600'}`}>
                {m.assignedTo ?? 'Unassigned'}
              </div>
            </div>
            {!m.assignedTo && (
              <button onClick={() => onStatusChange(m.id, 'assigned')}
                className="text-[11px] font-bold px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                Assign
              </button>
            )}
          </div>
        </div>

        {/* Vehicles card */}
        <div className="bg-white border border-slate-100 rounded-2xl overflow-hidden">
          <div className="px-5 pt-4 pb-3">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">
                Vehicles ({m.vehicles.length})
              </div>
              {hiddenCount > 0 && (
                <button onClick={() => setVehicleExpanded(e => !e)}
                  className="text-[10px] font-bold text-blue-500 hover:text-blue-700">
                  {vehicleExpanded ? 'Collapse ▲' : `Show ${hiddenCount} more ▼`}
                </button>
              )}
            </div>
            <div className="space-y-2">
              {shownVehicles.map(v => (
                <div key={v.stock} className="bg-slate-50 rounded-xl px-3.5 py-2.5">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-600 flex-shrink-0">
                      ↑OUT
                    </span>
                    <span className="font-mono text-[11px] font-bold text-blue-600 flex-shrink-0">#{v.stock}</span>
                    <span className="text-[12px] text-slate-700 flex-1 truncate">{v.year} {v.make} {v.model}</span>
                    <span className="text-[10px] text-slate-400 flex-shrink-0">{v.color}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px] pl-0.5">
                    <span className="text-slate-500">{v.fromZone}</span>
                    <svg width="10" height="10" fill="none" viewBox="0 0 24 24" className="flex-shrink-0 text-slate-300">
                      <path d="M5 12H19M13 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    <span className="text-blue-600 font-semibold">{v.toZone}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Timeline card */}
        <div className="bg-white border border-slate-100 rounded-2xl px-5 pt-4 pb-4">
          <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-3">Timeline</div>
          <div className="space-y-0">
            {m.timeline.map((ev, i) => (
              <div key={i} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                    ev.done ? 'bg-emerald-400' : ev.active ? 'bg-blue-500 ring-2 ring-blue-100' : 'bg-slate-200'
                  }`}>
                    {ev.done && (
                      <svg width="8" height="8" fill="none" viewBox="0 0 24 24">
                        <path d="M20 6 9 17l-5-5" stroke="white" strokeWidth="3.5" strokeLinecap="round"/>
                      </svg>
                    )}
                  </div>
                  {i < m.timeline.length - 1 && (
                    <div className={`w-px flex-1 mt-1 mb-1 ${ev.done ? 'bg-emerald-200' : 'bg-slate-100'}`} style={{ minHeight: '16px' }} />
                  )}
                </div>
                <div className="pb-3">
                  <div className={`text-[12px] font-semibold ${ev.done ? 'text-slate-700' : ev.active ? 'text-blue-700' : 'text-slate-400'}`}>
                    {ev.label}
                  </div>
                  {ev.sublabel && <div className="text-[10px] text-slate-400">{ev.sublabel}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Notes card */}
        {m.notes && (
          <div className="bg-white border border-slate-100 rounded-2xl px-5 pt-4 pb-4">
            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-2">Notes</div>
            <p className="text-[13px] text-slate-700 leading-relaxed">{m.notes}</p>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center gap-x-3 gap-y-1 text-[10px] text-slate-400 px-1 py-2 border-t border-slate-100 flex-wrap">
          <span>Requested by <span className="text-slate-500 font-medium">{m.requestedBy}</span></span>
          <span className="text-slate-200">·</span>
          <span>{m.requestedAt}</span>
          <span className="text-slate-200">·</span>
          <span>Updated {m.updatedLabel}</span>
        </div>

      </div>
    </div>
  )
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function VehicleMovement(): JSX.Element {
  const [view,       setView]       = useState<MoveStatus | 'all'>('all')
  const [search,     setSearch]     = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(MOVEMENTS[0]?.id ?? null)
  const [statuses,   setStatuses]   = useState<Record<string, MoveStatus>>({})

  const getStatus = (m: VehicleMovement): MoveStatus => statuses[m.id] ?? m.status

  const allWithStatus = useMemo(
    () => MOVEMENTS.map(m => ({ ...m, status: getStatus(m) })),
    [statuses],
  )

  const visible = useMemo(() => {
    const q = search.toLowerCase()
    return allWithStatus
      .filter(m => view === 'all' || m.status === view)
      .filter(m =>
        !q || [
          m.label, m.requestedBy, m.assignedTo ?? '',
          ...m.vehicles.map(v => `${v.make} ${v.model} ${v.stock}`),
        ].some(s => s.toLowerCase().includes(q))
      )
  }, [view, search, statuses])

  const selectedMovement =
    visible.find(m => m.id === selectedId) ??
    allWithStatus.find(m => m.id === selectedId)

  return (
    <div className="flex-1 flex overflow-hidden min-h-0">
      <Sidebar view={view} onView={setView} movements={allWithStatus} />

      {/* Center list */}
      <div
        className="flex-shrink-0 flex flex-col overflow-hidden border-r border-slate-200 bg-white"
        style={{ width: 'clamp(220px, 22vw, 290px)' }}>
        {/* Search */}
        <div className="px-3 py-2.5 border-b border-slate-200">
          <div className="relative">
            <svg width="12" height="12" fill="none" viewBox="0 0 24 24"
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400">
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8"/>
              <path d="m16.5 16.5 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
            </svg>
            <input
              value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search movements…"
              className="w-full h-7 pl-7 pr-2 text-[12px] bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 outline-none focus:border-blue-400 transition-colors"
            />
          </div>
        </div>
        <div className="flex items-center justify-between px-3 py-1.5 border-b border-slate-100">
          <span className="text-[11px] font-bold text-slate-700">Movements</span>
          <span className="text-[10px] text-slate-400">{visible.length}</span>
        </div>
        <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
          {visible.length === 0 ? (
            <div className="flex items-center justify-center h-24 text-[12px] text-slate-400">No movements found</div>
          ) : (
            visible.map(m => (
              <MovementRow
                key={m.id} m={m}
                selected={selectedId === m.id}
                onSelect={() => setSelectedId(m.id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Detail */}
      {selectedMovement ? (
        <MovementDetail
          key={selectedMovement.id}
          m={selectedMovement}
          onStatusChange={(id, s) => setStatuses(p => ({ ...p, [id]: s }))}
        />
      ) : (
        <div className="flex-1 flex items-center justify-center bg-slate-50 text-slate-400">
          <p className="text-[13px]">Select a movement</p>
        </div>
      )}
    </div>
  )
}
