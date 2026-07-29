// IncomingInventory.tsx — Tower Manager: Receiving workflow

import { useState, useMemo } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

type ArrivalStatus = 'expected' | 'scheduled' | 'arrived' | 'delayed' | 'unexpected'

interface IntakeStep {
  id: string; label: string; done: boolean
}

interface IncomingVehicle {
  id: string; stock: string; vin: string
  year: number; make: string; model: string; color: string
  carrier: string; source: string
  arrivalStatus: ArrivalStatus
  etaLabel: string; arrivedAt?: string
  intakeSteps: IntakeStep[]
  stagingZone?: string
  notes?: string
}

// ─── Data ─────────────────────────────────────────────────────────────────────

const VEHICLES: IncomingVehicle[] = [
  {
    id: 'iv1', stock: 'K28391', vin: '4T1BF1FK5HU712839', year: 2024, make: 'Toyota', model: 'Camry', color: 'Midnight Black',
    carrier: 'Axis Transport', source: 'Sunrise Toyota — Fullerton, CA',
    arrivalStatus: 'expected', etaLabel: 'Today 11:30 AM',
    intakeSteps: [
      { id: 's1', label: 'Vehicle arrived', done: false },
      { id: 's2', label: 'Keys received', done: false },
      { id: 's3', label: 'VIN verified', done: false },
      { id: 's4', label: 'Initial inspection complete', done: false },
      { id: 's5', label: 'Photos complete', done: false },
      { id: 's6', label: 'Fuel level checked', done: false },
      { id: 's7', label: 'Ready for staging', done: false },
    ],
  },
  {
    id: 'iv2', stock: 'K28392', vin: '1HGCV1F13LA019871', year: 2023, make: 'Honda', model: 'Accord', color: 'Lunar Silver',
    carrier: 'Auto Carriers Inc', source: 'Honda Regional Distribution — Ontario, CA',
    arrivalStatus: 'scheduled', etaLabel: 'Today 2:00 PM',
    intakeSteps: [
      { id: 's1', label: 'Vehicle arrived', done: false },
      { id: 's2', label: 'Keys received', done: false },
      { id: 's3', label: 'VIN verified', done: false },
      { id: 's4', label: 'Initial inspection complete', done: false },
      { id: 's5', label: 'Photos complete', done: false },
      { id: 's6', label: 'Fuel level checked', done: false },
      { id: 's7', label: 'Ready for staging', done: false },
    ],
  },
  {
    id: 'iv3', stock: 'K28393', vin: '5XYPH4A18MG188241', year: 2024, make: 'Kia', model: 'Telluride', color: 'Gravity Gray',
    carrier: 'Direct Auto Transport', source: 'Kia Motors America — Irvine, CA',
    arrivalStatus: 'delayed', etaLabel: 'Delayed — Was Today 9:00 AM',
    intakeSteps: [
      { id: 's1', label: 'Vehicle arrived', done: false },
      { id: 's2', label: 'Keys received', done: false },
      { id: 's3', label: 'VIN verified', done: false },
      { id: 's4', label: 'Initial inspection complete', done: false },
      { id: 's5', label: 'Photos complete', done: false },
      { id: 's6', label: 'Fuel level checked', done: false },
      { id: 's7', label: 'Ready for staging', done: false },
    ],
    notes: 'Carrier reported engine trouble on I-5. Estimated new arrival: Today 3:00 PM. Contact: Dispatch (714) 555-0199.',
  },
  {
    id: 'iv4', stock: 'A48291', vin: '1HGBH41JXMN109186', year: 2023, make: 'Honda', model: 'Accord', color: 'Sonic Gray Pearl',
    carrier: 'Pacific Auto Haulers', source: 'Crown Honda — Riverside, CA',
    arrivalStatus: 'arrived', etaLabel: 'Arrived 8:45 AM',
    arrivedAt: 'Today · 8:45 AM',
    intakeSteps: [
      { id: 's1', label: 'Vehicle arrived', done: true },
      { id: 's2', label: 'Keys received', done: true },
      { id: 's3', label: 'VIN verified', done: true },
      { id: 's4', label: 'Initial inspection complete', done: true },
      { id: 's5', label: 'Photos complete', done: false },
      { id: 's6', label: 'Fuel level checked', done: false },
      { id: 's7', label: 'Ready for staging', done: false },
    ],
    stagingZone: 'Receiving Bay A',
  },
  {
    id: 'iv5', stock: 'M29481', vin: '1FM5K8D82GGA22819', year: 2022, make: 'Ford', model: 'Explorer', color: 'Carbonized Gray',
    carrier: 'Western Auto Transport', source: 'AutoNation Ford — Corona, CA',
    arrivalStatus: 'arrived', etaLabel: 'Arrived Yesterday 4:20 PM',
    arrivedAt: 'Yesterday · 4:20 PM',
    intakeSteps: [
      { id: 's1', label: 'Vehicle arrived', done: true },
      { id: 's2', label: 'Keys received', done: true },
      { id: 's3', label: 'VIN verified', done: true },
      { id: 's4', label: 'Initial inspection complete', done: true },
      { id: 's5', label: 'Photos complete', done: true },
      { id: 's6', label: 'Fuel level checked', done: true },
      { id: 's7', label: 'Ready for staging', done: true },
    ],
    stagingZone: 'Ford Row C',
  },
  {
    id: 'iv6', stock: 'X19283', vin: 'JM3KFBDM0P0238192', year: 2024, make: 'Mazda', model: 'CX-5', color: 'Polymetal Gray',
    carrier: 'Unknown', source: 'Unscheduled — Walk-in',
    arrivalStatus: 'unexpected', etaLabel: 'Arrived 10:15 AM',
    arrivedAt: 'Today · 10:15 AM',
    intakeSteps: [
      { id: 's1', label: 'Vehicle arrived', done: true },
      { id: 's2', label: 'Keys received', done: true },
      { id: 's3', label: 'VIN verified', done: false },
      { id: 's4', label: 'Initial inspection complete', done: false },
      { id: 's5', label: 'Photos complete', done: false },
      { id: 's6', label: 'Fuel level checked', done: false },
      { id: 's7', label: 'Ready for staging', done: false },
    ],
    notes: 'Vehicle arrived unscheduled. VIN not found in DMS. Contact controller Sarah Kim to investigate.',
  },
  {
    id: 'iv7', stock: 'K28394', vin: 'WMWZC3C54JWE84721', year: 2024, make: 'BMW', model: 'X3', color: 'Alpine White',
    carrier: 'Premium Auto Logistics', source: 'AutoNation BMW — Buena Park, CA',
    arrivalStatus: 'scheduled', etaLabel: 'Tomorrow 10:00 AM',
    intakeSteps: [
      { id: 's1', label: 'Vehicle arrived', done: false },
      { id: 's2', label: 'Keys received', done: false },
      { id: 's3', label: 'VIN verified', done: false },
      { id: 's4', label: 'Initial inspection complete', done: false },
      { id: 's5', label: 'Photos complete', done: false },
      { id: 's6', label: 'Fuel level checked', done: false },
      { id: 's7', label: 'Ready for staging', done: false },
    ],
  },
]

// ─── Config ───────────────────────────────────────────────────────────────────

const statusCfg: Record<ArrivalStatus, { label: string; dot: string; text: string; bg: string; border: string }> = {
  expected:   { label: 'Expected',   dot: 'bg-blue-400',    text: 'text-blue-700',    bg: 'bg-blue-50',    border: '' },
  scheduled:  { label: 'Scheduled',  dot: 'bg-slate-400',   text: 'text-slate-600',   bg: 'bg-slate-100',  border: '' },
  arrived:    { label: 'Arrived',    dot: 'bg-emerald-400', text: 'text-emerald-700', bg: 'bg-emerald-50', border: '' },
  delayed:    { label: 'Delayed',    dot: 'bg-red-400',     text: 'text-red-700',     bg: 'bg-red-50',     border: 'border-l-2 border-l-red-400' },
  unexpected: { label: 'Unexpected', dot: 'bg-amber-400',   text: 'text-amber-700',   bg: 'bg-amber-50',   border: 'border-l-2 border-l-amber-400' },
}

const VIEWS: { id: ArrivalStatus | 'all'; label: string }[] = [
  { id: 'all',        label: "Today's Arrivals" },
  { id: 'expected',   label: 'Expected'         },
  { id: 'arrived',    label: 'Arrived'          },
  { id: 'delayed',    label: 'Delayed'          },
  { id: 'unexpected', label: 'Unexpected'       },
  { id: 'scheduled',  label: 'Scheduled'        },
]

// ─── Sub-components ───────────────────────────────────────────────────────────

function IntakeProgress({ steps }: { steps: IntakeStep[] }) {
  const done = steps.filter(s => s.done).length
  const pct  = Math.round((done / steps.length) * 100)
  const color = done === steps.length ? 'bg-emerald-400' : done > 0 ? 'bg-blue-500' : 'bg-slate-200'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-slate-100 overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] font-bold text-slate-500 flex-shrink-0">{done}/{steps.length}</span>
    </div>
  )
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function Sidebar({ view, onView }: { view: ArrivalStatus | 'all'; onView: (v: ArrivalStatus | 'all') => void }) {
  const count = (v: ArrivalStatus | 'all') =>
    v === 'all' ? VEHICLES.length : VEHICLES.filter(vv => vv.arrivalStatus === v).length

  return (
    <aside className="flex-shrink-0 w-44 bg-white border-r border-slate-200 flex flex-col py-3" style={{ scrollbarWidth: 'none' }}>
      <div className="text-[9px] font-bold uppercase tracking-widest text-slate-400 px-3 pb-1">Views</div>
      <div className="px-2 space-y-0.5">
        {VIEWS.map(vf => {
          const c = count(vf.id); const on = view === vf.id
          return (
            <button key={vf.id} onClick={() => onView(vf.id)}
              className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all ${on ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}>
              {vf.label}
              {c > 0 && <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${on ? 'bg-white/20' : 'bg-slate-100 text-slate-500'}`}>{c}</span>}
            </button>
          )
        })}
      </div>
    </aside>
  )
}

// ─── Vehicle list row ─────────────────────────────────────────────────────────

function VehicleRow({ v, selected, onSelect }: { v: IncomingVehicle; selected: boolean; onSelect: () => void }) {
  const sc = statusCfg[v.arrivalStatus]
  return (
    <button onClick={onSelect}
      className={`w-full text-left px-3 py-2.5 border-b border-slate-100 transition-all ${sc.border} ${selected ? 'bg-blue-50' : 'hover:bg-slate-50'}`}>
      {/* Row 1: vehicle + status */}
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="font-mono text-[11px] font-bold text-blue-600 flex-shrink-0">#{v.stock}</span>
          <span className={`text-[12px] font-semibold truncate ${selected ? 'text-blue-700' : 'text-slate-900'}`}>{v.year} {v.make} {v.model}</span>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <span className={`w-1.5 h-1.5 rounded-full ${sc.dot}`} />
          <span className={`text-[10px] font-semibold ${sc.text}`}>{sc.label}</span>
        </div>
      </div>
      {/* Row 2: carrier + eta */}
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10.5px] text-slate-400">{v.carrier}</span>
        <span className={`text-[10px] font-semibold ${v.arrivalStatus === 'delayed' ? 'text-red-600' : 'text-slate-500'}`}>{v.etaLabel}</span>
      </div>
      {/* Row 3: intake progress */}
      <IntakeProgress steps={v.intakeSteps} />
    </button>
  )
}

// ─── Intake detail panel ──────────────────────────────────────────────────────

function IntakeDetail({ v, onStepToggle }: { v: IncomingVehicle; onStepToggle: (vid: string, sid: string) => void }) {
  const sc = statusCfg[v.arrivalStatus]
  const done = v.intakeSteps.filter(s => s.done).length
  const pct  = Math.round((done / v.intakeSteps.length) * 100)
  const intakeComplete = done === v.intakeSteps.length

  function StatusActions() {
    if (v.arrivalStatus === 'expected' || v.arrivalStatus === 'scheduled') return (
      <div className="flex gap-2">
        <button className="text-[12px] font-bold px-4 py-1.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors">Mark Arrived</button>
        <button className="text-[12px] font-semibold px-4 py-1.5 bg-white text-slate-700 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors">Begin Intake</button>
      </div>
    )
    if (v.arrivalStatus === 'delayed') return (
      <div className="flex gap-2">
        <button className="text-[12px] font-bold px-4 py-1.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors">Mark Arrived</button>
        <button className="text-[12px] font-semibold px-3 py-1.5 text-slate-500 hover:text-slate-700 transition-colors">Update ETA</button>
      </div>
    )
    if (v.arrivalStatus === 'arrived' || v.arrivalStatus === 'unexpected') {
      if (intakeComplete) return (
        <div className="flex gap-2">
          <button className="text-[12px] font-bold px-4 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Assign Staging Zone</button>
          <button className="text-[12px] font-semibold px-4 py-1.5 bg-white text-slate-700 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors">View Vehicle</button>
        </div>
      )
      return (
        <div className="flex gap-2">
          <button className="text-[12px] font-bold px-4 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Continue Intake</button>
          {v.stagingZone && <button className="text-[12px] font-semibold px-4 py-1.5 bg-white text-slate-700 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors">View Vehicle</button>}
        </div>
      )
    }
    return null
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden min-h-0 bg-slate-50">
      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b border-slate-200 px-6 pt-4 pb-3">
        <div className="flex items-start gap-3 mb-3">
          <div>
            <h2 className="text-[17px] font-bold text-slate-900">{v.year} {v.make} {v.model}</h2>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              <span className="font-mono text-[11px] font-bold text-blue-600">#{v.stock}</span>
              <span className="text-[10px] text-slate-400">·</span>
              <span className={`w-1.5 h-1.5 rounded-full ${sc.dot}`} />
              <span className={`text-[11px] font-semibold ${sc.text}`}>{sc.label}</span>
              <span className={`text-[10px] font-semibold ${v.arrivalStatus === 'delayed' ? 'text-red-600' : 'text-slate-500'}`}>{v.etaLabel}</span>
            </div>
          </div>
        </div>
        <StatusActions />
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3" style={{ scrollbarWidth: 'thin' }}>

        {/* Vehicle summary */}
        <div className="bg-white border border-slate-100 rounded-2xl overflow-hidden">
          <div className="grid grid-cols-2 gap-0 divide-x divide-slate-100">
            <div className="px-4 py-3">
              <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">VIN</div>
              <div className="font-mono text-[11px] text-slate-700 font-semibold">{v.vin}</div>
            </div>
            <div className="px-4 py-3">
              <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Color</div>
              <div className="text-[12px] text-slate-700 font-semibold">{v.color}</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-0 divide-x divide-slate-100 border-t border-slate-100">
            <div className="px-4 py-3">
              <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Source</div>
              <div className="text-[11px] text-slate-700 font-semibold leading-snug">{v.source}</div>
            </div>
            <div className="px-4 py-3">
              <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Carrier</div>
              <div className="text-[12px] text-slate-700 font-semibold">{v.carrier}</div>
            </div>
          </div>
          {(v.arrivedAt || v.stagingZone) && (
            <div className="grid grid-cols-2 gap-0 divide-x divide-slate-100 border-t border-slate-100">
              {v.arrivedAt && (
                <div className="px-4 py-3">
                  <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Arrived</div>
                  <div className="text-[12px] text-slate-700 font-semibold">{v.arrivedAt}</div>
                </div>
              )}
              {v.stagingZone && (
                <div className="px-4 py-3">
                  <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Staging Zone</div>
                  <div className="text-[12px] text-slate-700 font-semibold">{v.stagingZone}</div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Intake checklist */}
        <div className="bg-white border border-slate-100 rounded-2xl px-5 pt-4 pb-4">
          <div className="flex items-center justify-between mb-1">
            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Intake Checklist</div>
            <span className={`text-[10px] font-bold ${intakeComplete ? 'text-emerald-600' : 'text-slate-500'}`}>{pct}%</span>
          </div>
          {/* Progress bar */}
          <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden mb-3">
            <div className={`h-full rounded-full transition-all ${intakeComplete ? 'bg-emerald-400' : 'bg-blue-500'}`} style={{ width: `${pct}%` }} />
          </div>
          <div className="space-y-1">
            {v.intakeSteps.map(step => (
              <button key={step.id} onClick={() => onStepToggle(v.id, step.id)}
                className="w-full flex items-center gap-3 text-left hover:bg-slate-50 rounded-xl px-3 py-2.5 transition-colors group">
                <span className={`w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 border-2 transition-colors ${
                  step.done ? 'bg-emerald-500 border-emerald-500' : 'border-slate-300 group-hover:border-blue-400'
                }`}>
                  {step.done && <svg width="9" height="9" fill="none" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" stroke="white" strokeWidth="3.5" strokeLinecap="round"/></svg>}
                </span>
                <span className={`text-[13px] ${step.done ? 'text-slate-400 line-through' : 'text-slate-800'}`}>{step.label}</span>
                {step.done && <span className="ml-auto text-[9px] font-bold text-emerald-600">✓</span>}
              </button>
            ))}
          </div>
        </div>

        {/* Activity timeline */}
        <div className="bg-white border border-slate-100 rounded-2xl px-5 pt-4 pb-4">
          <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-3">Activity</div>
          <div className="space-y-0">
            {[
              ...(v.arrivedAt ? [{ label: `Vehicle arrived`, sub: v.arrivedAt, done: true }] : []),
              ...(done > 0 ? [{ label: `Intake started — ${done} steps completed`, sub: 'Today', done: true }] : []),
              ...(v.stagingZone ? [{ label: `Staged at ${v.stagingZone}`, sub: 'Today', done: true }] : []),
              { label: v.arrivalStatus === 'arrived' || v.arrivalStatus === 'unexpected' ? 'Awaiting intake completion' : 'Awaiting arrival', sub: '', done: false, active: true },
            ].map((ev, i, arr) => (
              <div key={i} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className={`w-3.5 h-3.5 rounded-full flex-shrink-0 mt-0.5 ${ev.done ? 'bg-emerald-400' : ev.active ? 'bg-blue-400 ring-2 ring-blue-100' : 'bg-slate-200'}`} />
                  {i < arr.length - 1 && <div className={`w-px flex-1 mt-1 mb-1 ${ev.done ? 'bg-emerald-100' : 'bg-slate-100'}`} style={{ minHeight: '12px' }} />}
                </div>
                <div className="pb-2.5">
                  <div className={`text-[12px] font-medium ${ev.done ? 'text-slate-700' : ev.active ? 'text-blue-600' : 'text-slate-400'}`}>{ev.label}</div>
                  {ev.sub && <div className="text-[10px] text-slate-400">{ev.sub}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Notes */}
        {v.notes && (
          <div className="bg-amber-50 border border-amber-100 rounded-2xl px-5 pt-4 pb-4">
            <div className="text-[9px] font-bold text-amber-500 uppercase tracking-widest mb-2">Note</div>
            <p className="text-[13px] text-slate-700 leading-relaxed">{v.notes}</p>
          </div>
        )}

      </div>
    </div>
  )
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function IncomingInventory() {
  const [view,       setView]       = useState<ArrivalStatus | 'all'>('all')
  const [search,     setSearch]     = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(VEHICLES[0]?.id ?? null)
  const [stepState,  setStepState]  = useState<Record<string, Record<string, boolean>>>({})

  // Merge interactive step state into vehicle data
  const vehicles = useMemo(() =>
    VEHICLES.map(v => ({
      ...v,
      intakeSteps: v.intakeSteps.map(s => ({
        ...s,
        done: stepState[v.id]?.[s.id] !== undefined ? stepState[v.id][s.id] : s.done,
      })),
    }))
  , [stepState])

  const visible = useMemo(() => {
    const q = search.toLowerCase()
    return vehicles
      .filter(v => view === 'all' || v.arrivalStatus === view)
      .filter(v => !q || [v.stock, v.vin, v.make, v.model, v.carrier, v.source].some(s => s.toLowerCase().includes(q)))
  }, [vehicles, view, search])

  const selected = visible.find(v => v.id === selectedId) ?? vehicles.find(v => v.id === selectedId)

  function handleStepToggle(vid: string, sid: string) {
    setStepState(prev => {
      const vState = prev[vid] ?? {}
      const veh = vehicles.find(v => v.id === vid)!
      const currentDone = vState[sid] !== undefined ? vState[sid] : veh.intakeSteps.find(s => s.id === sid)!.done
      return { ...prev, [vid]: { ...vState, [sid]: !currentDone } }
    })
  }

  return (
    <div className="flex-1 flex overflow-hidden min-h-0">
      <Sidebar view={view} onView={setView} />

      {/* Center list */}
      <div className="flex-shrink-0 flex flex-col overflow-hidden border-r border-slate-200 bg-white" style={{ width: 'clamp(220px, 22vw, 290px)' }}>
        {/* Search */}
        <div className="px-3 py-2.5 border-b border-slate-200">
          <div className="relative">
            <svg width="12" height="12" fill="none" viewBox="0 0 24 24" className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400">
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8"/><path d="m16.5 16.5 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
            </svg>
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search vehicles…"
              className="w-full h-7 pl-7 pr-2 text-[12px] bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 outline-none focus:border-blue-400 transition-colors" />
          </div>
        </div>
        <div className="flex items-center justify-between px-3 py-1.5 border-b border-slate-100">
          <span className="text-[11px] font-bold text-slate-700">Incoming Vehicles</span>
          <span className="text-[10px] text-slate-400">{visible.length}</span>
        </div>
        <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
          {visible.length === 0 ? (
            <div className="flex items-center justify-center h-24 text-[12px] text-slate-400">No vehicles</div>
          ) : (
            visible.map(v => <VehicleRow key={v.id} v={v} selected={selectedId === v.id} onSelect={() => setSelectedId(v.id)} />)
          )}
        </div>
      </div>

      {/* Detail */}
      {selected ? (
        <IntakeDetail key={selected.id} v={selected} onStepToggle={handleStepToggle} />
      ) : (
        <div className="flex-1 flex items-center justify-center bg-slate-50 text-slate-400">
          <p className="text-[13px]">Select a vehicle</p>
        </div>
      )}
    </div>
  )
}
