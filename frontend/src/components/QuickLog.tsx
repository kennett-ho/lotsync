import { useState, useRef, useEffect, useCallback } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

type ActionId =
  // Inventory
  | 'delivered' | 'moved' | 'located' | 'tag' | 'fueled' | 'ready'
  // Devices
  | 'recovr' | 'mdd' | 'device-removed'
  // Dealer Trade
  | 'trade-arrived' | 'trade-departed'
  // Sales
  | 'pull-vehicle' | 'delivery-ready' | 'showroom'
  // Exceptions
  | 'damage' | 'missing-tag' | 'wrong-location' | 'other-issue'
  // General
  | 'note'

type Step = 'action' | 'vehicle' | 'details' | 'review' | 'done'
type VehicleMode = 'last6' | 'stock' | 'full'

interface FoundVehicle {
  vin: string; stock: string; make: string; model: string; year: number; location: string
}

interface ActionDef {
  id: ActionId; label: string; desc: string; emoji: string
}

interface ActionCategory {
  label: string; color: string; actions: ActionDef[]
}

// ─── Mock vehicle lookup ──────────────────────────────────────────────────────

const MOCK_VEHICLES: Record<string, FoundVehicle> = {
  'A48291': { vin: '1HGCM82633A004352', stock: 'A48291', make: 'Honda', model: 'Accord EX-L', year: 2023, location: 'Row 4, Space 12' },
  'B93021': { vin: '3VWFE21C04M000001', stock: 'B93021', make: 'Volkswagen', model: 'Jetta SE', year: 2022, location: 'Row 2, Space 7' },
  'F38102': { vin: '1FTEW1E53JKD03928', stock: 'F38102', make: 'Ford', model: 'F-150 XLT', year: 2021, location: 'Row 7, Space 3' },
  'G10923': { vin: 'JTHBF30G175031729', stock: 'G10923', make: 'Lexus', model: 'ES 350', year: 2023, location: 'Row 1, Space 14' },
}

function lookupVehicle(query: string): FoundVehicle | null {
  const q = query.trim().toUpperCase()
  if (q.length < 4) return null
  if (MOCK_VEHICLES[q]) return MOCK_VEHICLES[q]
  return MOCK_VEHICLES['A48291']
}

// ─── Action categories ────────────────────────────────────────────────────────

const CATEGORIES: ActionCategory[] = [
  {
    label: 'Inventory',
    color: 'text-blue-600 bg-blue-50',
    actions: [
      { id: 'delivered',  label: 'Vehicle Delivered',   desc: 'Record an incoming vehicle arrival on the lot.',         emoji: '🚚' },
      { id: 'moved',      label: 'Vehicle Moved',        desc: 'Update the lot location after physically moving a car.',  emoji: '🚗' },
      { id: 'located',    label: 'Vehicle Located',      desc: 'Confirm a vehicle was found at its recorded position.',   emoji: '📍' },
      { id: 'tag',        label: 'Stock Tag Replaced',   desc: 'Record that a new lot tag was placed on the vehicle.',    emoji: '🏷️' },
      { id: 'fueled',     label: 'Vehicle Fueled',       desc: 'Log the fuel level after filling up a vehicle.',         emoji: '⛽' },
      { id: 'ready',      label: 'Vehicle Ready',        desc: 'Mark this vehicle as prepared for frontline sales.',      emoji: '🟢' },
    ],
  },
  {
    label: 'Devices',
    color: 'text-violet-600 bg-violet-50',
    actions: [
      { id: 'recovr',         label: 'RecovR Installed',  desc: 'Record that a RecovR GPS device was physically installed.',  emoji: '📡' },
      { id: 'mdd',            label: 'MDD Installed',     desc: 'Record that an MDD beacon device was physically installed.', emoji: '📶' },
      { id: 'device-removed', label: 'Device Removed',    desc: 'Log that a tracking device was removed from the vehicle.',   emoji: '🔧' },
    ],
  },
  {
    label: 'Dealer Trade',
    color: 'text-indigo-600 bg-indigo-50',
    actions: [
      { id: 'trade-arrived',   label: 'Trade Arrived',   desc: 'Log an incoming dealer trade vehicle being received.',   emoji: '📥' },
      { id: 'trade-departed',  label: 'Trade Departed',  desc: 'Log a vehicle that has left the lot for a dealer trade.', emoji: '📤' },
    ],
  },
  {
    label: 'Sales',
    color: 'text-emerald-600 bg-emerald-50',
    actions: [
      { id: 'pull-vehicle',    label: 'Vehicle Pulled Up',      desc: 'Record that a vehicle was staged for a customer.',        emoji: '🅿️' },
      { id: 'delivery-ready',  label: 'Delivery Ready',         desc: 'Confirm the vehicle is fully prepped for customer handoff.', emoji: '🎀' },
      { id: 'showroom',        label: 'Showroom Placement',     desc: 'Log that a vehicle was moved into the showroom.',          emoji: '🏢' },
    ],
  },
  {
    label: 'Exceptions',
    color: 'text-red-600 bg-red-50',
    actions: [
      { id: 'damage',         label: 'Damage Found',       desc: 'Report physical damage observed on a vehicle.',                    emoji: '⚠️' },
      { id: 'missing-tag',    label: 'Missing Stock Tag',  desc: 'Flag that a lot tag is absent and needs replacement.',             emoji: '❌' },
      { id: 'wrong-location', label: 'Wrong Location',     desc: 'Record that the vehicle was found somewhere unexpected.',           emoji: '❓' },
      { id: 'other-issue',    label: 'Other Issue',        desc: 'Flag an operational problem that doesn\'t fit another category.',  emoji: '🚩' },
    ],
  },
  {
    label: 'General',
    color: 'text-slate-600 bg-slate-100',
    actions: [
      { id: 'note', label: 'General Note', desc: 'Attach a free-form note to a vehicle\'s activity timeline.', emoji: '📝' },
    ],
  },
]

const ALL_ACTIONS: ActionDef[] = CATEGORIES.flatMap(c => c.actions)

function getAction(id: ActionId): ActionDef {
  return ALL_ACTIONS.find(a => a.id === id) ?? { id, label: id, desc: '', emoji: '📋' }
}

// ─── Icons ────────────────────────────────────────────────────────────────────

const I = {
  close:   <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>,
  back:    <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="m15 18-6-6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  search:  <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8"/><path d="m16.5 16.5 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>,
  check:   <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  camera:  <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" stroke="currentColor" strokeWidth="1.75"/><circle cx="12" cy="13" r="4" stroke="currentColor" strokeWidth="1.75"/></svg>,
  plus:    <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/></svg>,
  car:     <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M5 17H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h13l4 4v4a2 2 0 0 1-2 2h-2M5 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0zM15 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"/></svg>,
  barcode: <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M3 9V6a1 1 0 0 1 1-1h3M3 15v3a1 1 0 0 0 1 1h3M15 5h3a1 1 0 0 1 1 1v3M15 19h3a1 1 0 0 0 1-1v-3M7 8v8M10 8v8M13 8v8M16 8v8" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></svg>,
  pin:     <svg width="11" height="11" fill="none" viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" stroke="currentColor" strokeWidth="1.75"/><circle cx="12" cy="10" r="3" stroke="currentColor" strokeWidth="1.75"/></svg>,
  user:    <svg width="11" height="11" fill="none" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="currentColor" strokeWidth="1.75"/><circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="1.75"/></svg>,
  clock:   <svg width="11" height="11" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.75"/><path d="M12 6v6l4 2" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></svg>,
}

// ─── Step indicator ───────────────────────────────────────────────────────────

const STEP_LABELS: Partial<Record<Step, string>> = {
  action: 'Activity',
  vehicle: 'Vehicle',
  details: 'Details',
  review: 'Review',
}

function StepIndicator({ current, action }: { current: Step; action: ActionId | null }) {
  const steps: Step[] = ['action', 'vehicle', 'details', 'review']
  const currentIdx = steps.indexOf(current)

  return (
    <div className="flex items-center gap-1.5 px-5 py-3 border-b border-slate-100 bg-slate-50/50">
      {steps.map((s, i) => {
        const done = currentIdx > i
        const active = currentIdx === i
        return (
          <div key={s} className="flex items-center gap-1.5">
            <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-all ${
              done ? 'bg-blue-600 text-white' : active ? 'bg-blue-600 text-white ring-2 ring-blue-200' : 'bg-slate-200 text-slate-400'
            }`}>
              {done ? <span className="scale-90">{I.check}</span> : i + 1}
            </div>
            <span className={`text-[11px] font-semibold ${active ? 'text-blue-700' : done ? 'text-slate-500' : 'text-slate-400'}`}>
              {s === 'details' && action ? getAction(action).label : STEP_LABELS[s]}
            </span>
            {i < steps.length - 1 && <div className={`w-5 h-px mx-0.5 ${i < currentIdx ? 'bg-blue-300' : 'bg-slate-200'}`} />}
          </div>
        )
      })}
    </div>
  )
}

// ─── Step 1: Action picker ────────────────────────────────────────────────────

function ActionStep({ onSelect }: { onSelect: (id: ActionId) => void }) {
  const [hovered, setHovered] = useState<ActionId | null>(null)

  return (
    <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5" style={{ scrollbarWidth: 'thin' }}>
      <p className="text-[12px] text-slate-400">Choose what to log — only record what automated systems can't capture on their own.</p>
      {CATEGORIES.map(cat => (
        <div key={cat.label}>
          <div className="flex items-center gap-2 mb-2.5">
            <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${cat.color}`}>{cat.label}</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {cat.actions.map(action => {
              const isHovered = hovered === action.id
              return (
                <button key={action.id}
                  onClick={() => onSelect(action.id)}
                  onMouseEnter={() => setHovered(action.id)}
                  onMouseLeave={() => setHovered(null)}
                  className={`flex items-start gap-2.5 p-3.5 bg-white rounded-xl border text-left transition-all duration-150 group ${
                    isHovered ? 'border-blue-300 bg-blue-50/50 shadow-sm' : 'border-slate-200 hover:border-blue-200'
                  }`}>
                  <span className="text-xl flex-shrink-0 leading-none mt-0.5">{action.emoji}</span>
                  <div className="min-w-0">
                    <div className={`text-[12px] font-bold leading-tight transition-colors ${isHovered ? 'text-blue-800' : 'text-slate-900'}`}>
                      {action.label}
                    </div>
                    <div className={`text-[10px] mt-1 leading-snug transition-colors ${isHovered ? 'text-blue-600/80' : 'text-slate-400'}`}>
                      {action.desc}
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

// ─── Step 2: Vehicle identification ──────────────────────────────────────────

function VehicleStep({ onFound, onContinue }: { onFound: (v: FoundVehicle) => void; onContinue: (v: FoundVehicle) => void }) {
  const [mode, setMode] = useState<VehicleMode>('last6')
  const [query, setQuery] = useState('')
  const [found, setFound] = useState<FoundVehicle | null>(null)
  const [scanning, setScanning] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  const handleQuery = useCallback((val: string) => {
    setQuery(val)
    const v = lookupVehicle(val)
    setFound(v)
    if (v) onFound(v)
  }, [onFound])

  const handleScan = () => {
    setScanning(true)
    setTimeout(() => {
      setScanning(false)
      const v = MOCK_VEHICLES['A48291']
      setQuery('004352')
      setFound(v)
      onFound(v)
    }, 1400)
  }

  const modeLabels: Record<VehicleMode, string> = { last6: 'Last 6 VIN', stock: 'Stock #', full: 'Full VIN' }
  const placeholders: Record<VehicleMode, string> = { last6: '004352', stock: 'A48291', full: '1HGCM82633A004352' }

  return (
    <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4" style={{ scrollbarWidth: 'thin' }}>
      <p className="text-[12px] text-slate-400">Identify the vehicle — search by VIN or stock number</p>

      <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1 w-fit">
        {(Object.keys(modeLabels) as VehicleMode[]).map(m => (
          <button key={m} onClick={() => { setMode(m); setQuery(''); setFound(null) }}
            className={`text-[11px] font-semibold px-3 py-1.5 rounded-md transition-all ${mode === m ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
            {modeLabels[m]}
          </button>
        ))}
      </div>

      <div className="space-y-2">
        <div className="relative">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">{I.search}</span>
          <input
            ref={inputRef}
            value={query}
            onChange={e => handleQuery(e.target.value)}
            placeholder={placeholders[mode]}
            maxLength={mode === 'last6' ? 6 : mode === 'stock' ? 8 : 17}
            className="w-full h-12 pl-10 pr-24 text-[15px] font-mono font-semibold bg-white border border-slate-200 rounded-xl text-slate-900 placeholder:text-slate-300 placeholder:font-normal outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all uppercase"
          />
          <button onClick={handleScan} disabled={scanning}
            className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 text-[11px] font-bold text-slate-500 hover:text-blue-600 bg-slate-100 hover:bg-blue-50 border border-slate-200 hover:border-blue-300 px-2.5 py-1 rounded-lg transition-all">
            {scanning ? <span className="animate-spin text-blue-500">{I.barcode}</span> : I.barcode}
            {scanning ? 'Scanning…' : 'Scan'}
          </button>
        </div>
        {mode === 'last6' && (
          <p className="text-[11px] text-slate-400 pl-1">Enter the last 6 of the VIN — e.g. <span className="font-mono">004352</span></p>
        )}
      </div>

      {found && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-100 flex items-center justify-center flex-shrink-0">
              <span className="text-emerald-600">{I.car}</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-[12px] font-bold text-emerald-700">Vehicle found</span>
                <span className="text-emerald-500">{I.check}</span>
              </div>
              <div className="text-[15px] font-bold text-slate-900">{found.year} {found.make} {found.model}</div>
              <div className="flex items-center gap-3 mt-1">
                <span className="font-mono text-[12px] font-bold text-blue-600 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded">{found.stock}</span>
                <span className="flex items-center gap-1 text-[11px] text-slate-500">{I.pin} {found.location}</span>
              </div>
              <div className="font-mono text-[10px] text-slate-400 mt-1">{found.vin}</div>
            </div>
          </div>
        </div>
      )}

      {query.length >= 4 && !found && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 text-[12px] text-amber-700">
          No vehicle found for <span className="font-mono font-bold">{query}</span>. Try a different identifier.
        </div>
      )}

      <button onClick={() => found && onContinue(found)} disabled={!found}
        className={`w-full h-11 rounded-xl text-[13px] font-bold transition-all ${
          found ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm' : 'bg-slate-100 text-slate-400 cursor-not-allowed'
        }`}>
        {found ? `Continue with ${found.make} ${found.model}` : 'Identify vehicle to continue'}
      </button>
    </div>
  )
}

// ─── Step 3: Details forms ────────────────────────────────────────────────────

const DELIVERY_SOURCES = ['Manufacturer', 'Auction', 'Dealer Trade', 'Customer Trade', 'Other']
const DAMAGE_SEVERITY  = ['Minor', 'Moderate', 'Severe']
const DAMAGE_LOCATION  = ['Front', 'Rear', 'Driver Side', 'Passenger Side', 'Interior', 'Other']
const FUEL_LEVELS      = ['1/4', '1/2', '3/4', 'Full']

function VehicleChip({ vehicle }: { vehicle: FoundVehicle }) {
  return (
    <div className="flex items-center gap-3 bg-slate-50 border border-slate-200 rounded-xl p-3 mb-2">
      <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
        <span className="text-blue-600">{I.car}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[13px] font-bold text-slate-900">{vehicle.year} {vehicle.make} {vehicle.model}</div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="font-mono text-[11px] font-bold text-blue-600">{vehicle.stock}</span>
          <span className="text-[10px] text-slate-400">·</span>
          <span className="flex items-center gap-1 text-[11px] text-slate-400">{I.pin} {vehicle.location}</span>
        </div>
      </div>
    </div>
  )
}

function ChipGroup({ options, value, onChange, multi = false }: {
  options: string[]; value: string | string[]; onChange: (v: string | string[]) => void; multi?: boolean
}) {
  const selected = Array.isArray(value) ? value : [value]
  const toggle = (opt: string) => {
    if (multi) {
      const arr = selected.includes(opt) ? selected.filter(s => s !== opt) : [...selected, opt]
      onChange(arr)
    } else {
      onChange(opt)
    }
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map(opt => {
        const active = selected.includes(opt)
        return (
          <button key={opt} onClick={() => toggle(opt)}
            className={`text-[12px] font-semibold px-3 py-1.5 rounded-lg border transition-all ${
              active ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-600 border-slate-200 hover:border-blue-300 hover:text-blue-600'
            }`}>
            {opt}
          </button>
        )
      })}
    </div>
  )
}

function PhotoUpload({ count, onAdd }: { count: number; onAdd: () => void }) {
  return (
    <button onClick={onAdd}
      className="w-full h-20 border-2 border-dashed border-slate-200 hover:border-blue-300 hover:bg-blue-50/30 rounded-xl flex flex-col items-center justify-center gap-1.5 transition-all group">
      <span className="text-slate-400 group-hover:text-blue-500">{I.camera}</span>
      <span className="text-[12px] font-semibold text-slate-400 group-hover:text-blue-600">
        {count > 0 ? `${count} photo${count > 1 ? 's' : ''} — tap to add more` : 'Tap to add photos'}
      </span>
    </button>
  )
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="text-[12px] font-bold text-slate-700 block mb-1.5">{children}</label>
}

function TextInput({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
      className="w-full h-10 px-3 text-[13px] bg-white border border-slate-200 rounded-xl text-slate-800 placeholder:text-slate-300 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all" />
  )
}

// Subset of fields actually used — keeps details minimal per action
interface DetailsState {
  source: string; fromLoc: string; toLoc: string; location: string
  dealer: string; severity: string; damageLocation: string[]
  photoCount: number; notes: string; fuelLevel: string
}

function DetailsStep({ action, vehicle, onNext }: {
  action: ActionId; vehicle: FoundVehicle; onNext: (data: DetailsState) => void
}) {
  const [s, setS] = useState<DetailsState>({
    source: '', fromLoc: vehicle.location, toLoc: '', location: '',
    dealer: '', severity: '', damageLocation: [], photoCount: 0,
    notes: '', fuelLevel: '',
  })
  const set = <K extends keyof DetailsState>(k: K) => (v: DetailsState[K]) => setS(prev => ({ ...prev, [k]: v }))

  const canSave = (): boolean => {
    switch (action) {
      case 'delivered':       return s.source !== ''
      case 'moved':           return s.toLoc.trim() !== ''
      case 'located':         return s.location.trim() !== ''
      case 'fueled':          return s.fuelLevel !== ''
      case 'trade-arrived':
      case 'trade-departed':  return s.dealer.trim() !== ''
      case 'damage':          return s.severity !== '' && s.notes.trim() !== ''
      case 'note':            return s.notes.trim() !== ''
      default:                return true
    }
  }

  // Determine if this action queues a verification (shown as info nudge)
  const needsVerification = ['recovr', 'mdd', 'tag'].includes(action)

  return (
    <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4" style={{ scrollbarWidth: 'thin' }}>
      <VehicleChip vehicle={vehicle} />

      {needsVerification && (
        <div className="flex items-start gap-2.5 bg-amber-50 border border-amber-200 rounded-xl px-3.5 py-3">
          <span className="text-amber-500 mt-0.5">
            <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.75"/><path d="M12 8v4M12 16h.01" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></svg>
          </span>
          <p className="text-[11px] text-amber-700 leading-relaxed">
            This activity will be queued for <span className="font-bold">verification</span> during the next Inventory Sync.
            LotSync will confirm it automatically.
          </p>
        </div>
      )}

      {action === 'delivered' && (
        <div>
          <FieldLabel>Delivery source <span className="text-red-500">*</span></FieldLabel>
          <ChipGroup options={DELIVERY_SOURCES} value={s.source} onChange={set('source') as (v: string | string[]) => void} />
        </div>
      )}

      {action === 'moved' && (
        <div className="space-y-3">
          <div><FieldLabel>Moving from</FieldLabel><TextInput value={s.fromLoc} onChange={set('fromLoc')} /></div>
          <div><FieldLabel>New location <span className="text-red-500">*</span></FieldLabel><TextInput value={s.toLoc} onChange={set('toLoc')} placeholder="e.g. Row 2, Space 4" /></div>
        </div>
      )}

      {action === 'located' && (
        <div>
          <FieldLabel>Confirmed location <span className="text-red-500">*</span></FieldLabel>
          <TextInput value={s.location} onChange={set('location')} placeholder="e.g. Row 4, Space 12" />
        </div>
      )}

      {action === 'fueled' && (
        <div>
          <FieldLabel>Fuel level after <span className="text-red-500">*</span></FieldLabel>
          <ChipGroup options={FUEL_LEVELS} value={s.fuelLevel} onChange={set('fuelLevel') as (v: string | string[]) => void} />
        </div>
      )}

      {(action === 'trade-arrived' || action === 'trade-departed') && (
        <div>
          <FieldLabel>{action === 'trade-arrived' ? 'Arriving from dealer' : 'Departing to dealer'} <span className="text-red-500">*</span></FieldLabel>
          <TextInput value={s.dealer} onChange={set('dealer')} placeholder="e.g. Central Honda" />
        </div>
      )}

      {action === 'damage' && (
        <div className="space-y-3">
          <div><FieldLabel>Photos</FieldLabel><PhotoUpload count={s.photoCount} onAdd={() => set('photoCount')(s.photoCount + 1)} /></div>
          <div><FieldLabel>Severity <span className="text-red-500">*</span></FieldLabel><ChipGroup options={DAMAGE_SEVERITY} value={s.severity} onChange={set('severity') as (v: string | string[]) => void} /></div>
          <div><FieldLabel>Location on vehicle</FieldLabel><ChipGroup options={DAMAGE_LOCATION} value={s.damageLocation} onChange={set('damageLocation') as (v: string | string[]) => void} multi /></div>
        </div>
      )}

      {(action === 'missing-tag' || action === 'wrong-location' || action === 'other-issue') && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3.5 text-[12px] text-red-700 font-semibold">
          This exception will be flagged to your lot manager.
        </div>
      )}

      {/* Simple confirmation for actions with no required fields */}
      {(['tag', 'ready', 'recovr', 'mdd', 'device-removed', 'pull-vehicle', 'delivery-ready', 'showroom'] as ActionId[]).includes(action) && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-[13px] text-slate-600">
          Activity will be logged on <span className="font-bold text-slate-900">{vehicle.stock}</span>. Add an optional note below.
        </div>
      )}

      <div>
        <label className="text-[12px] font-bold text-slate-700 block mb-1.5">
          {action === 'note' ? <>Notes <span className="text-red-500">*</span></> : 'Notes (optional)'}
        </label>
        <textarea value={s.notes} onChange={e => setS(prev => ({ ...prev, notes: e.target.value }))}
          rows={action === 'note' ? 4 : 2}
          placeholder={action === 'note' ? 'Enter your note…' : 'Add additional context…'}
          className="w-full px-3 py-2.5 text-[13px] bg-white border border-slate-200 rounded-xl text-slate-800 placeholder:text-slate-300 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all resize-none" />
      </div>

      <button onClick={() => canSave() && onNext(s)} disabled={!canSave()}
        className={`w-full h-11 rounded-xl text-[13px] font-bold transition-all ${
          canSave() ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm' : 'bg-slate-100 text-slate-400 cursor-not-allowed'
        }`}>
        Review & Save
      </button>
    </div>
  )
}

// ─── Step 4: Review ───────────────────────────────────────────────────────────

function ReviewStep({ action, vehicle, details, onConfirm, onBack }: {
  action: ActionId; vehicle: FoundVehicle; details: DetailsState
  onConfirm: () => void; onBack: () => void
}) {
  const act = getAction(action)
  const needsVerification = ['recovr', 'mdd', 'tag'].includes(action)

  const detailSummary = (): string | null => {
    switch (action) {
      case 'delivered':       return details.source ? `Source: ${details.source}` : null
      case 'moved':           return details.toLoc ? `Moving to: ${details.toLoc}` : null
      case 'located':         return details.location ? `Location: ${details.location}` : null
      case 'fueled':          return details.fuelLevel ? `Fuel level: ${details.fuelLevel}` : null
      case 'trade-arrived':   return details.dealer ? `From: ${details.dealer}` : null
      case 'trade-departed':  return details.dealer ? `To: ${details.dealer}` : null
      case 'damage':          return details.severity
        ? `Severity: ${details.severity}${details.damageLocation.length > 0 ? ' · ' + details.damageLocation.join(', ') : ''}`
        : null
      default: return null
    }
  }

  const now = new Date()
  const timeStr = now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
  const summary = detailSummary()

  return (
    <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4" style={{ scrollbarWidth: 'thin' }}>
      <p className="text-[12px] text-slate-400">Review before saving</p>

      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden divide-y divide-slate-100">
        <div className="px-4 py-3 flex items-center gap-3">
          <span className="text-2xl">{act.emoji}</span>
          <div>
            <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Activity</div>
            <div className="text-[14px] font-bold text-slate-900">{act.label}</div>
          </div>
        </div>

        <div className="px-4 py-3">
          <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-1">Vehicle</div>
          <div className="text-[14px] font-bold text-slate-900">{vehicle.year} {vehicle.make} {vehicle.model}</div>
          <div className="flex items-center gap-2 mt-1">
            <span className="font-mono text-[12px] font-bold text-blue-600 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded">{vehicle.stock}</span>
            <span className="flex items-center gap-1 text-[11px] text-slate-400">{I.pin} {vehicle.location}</span>
          </div>
          <div className="font-mono text-[10px] text-slate-400 mt-1">{vehicle.vin}</div>
        </div>

        {summary && (
          <div className="px-4 py-3">
            <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-0.5">Details</div>
            <div className="text-[13px] text-slate-800 font-semibold">{summary}</div>
          </div>
        )}

        {details.notes && (
          <div className="px-4 py-3">
            <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-0.5">Notes</div>
            <div className="text-[13px] text-slate-700">{details.notes}</div>
          </div>
        )}

        <div className="px-4 py-2.5 bg-slate-50/70 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
            {I.user} Marcus Torres
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
            {I.clock} Now · {timeStr}
          </div>
        </div>
      </div>

      {needsVerification && (
        <div className="flex items-start gap-2.5 bg-amber-50 border border-amber-200 rounded-xl px-3.5 py-3">
          <span className="text-amber-500 mt-0.5 flex-shrink-0">
            <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.75"/><path d="M12 8v4M12 16h.01" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></svg>
          </span>
          <p className="text-[11px] text-amber-700 leading-relaxed">
            This will appear in <span className="font-bold">Verification Needed</span> on your dashboard until the next Inventory Sync confirms it.
          </p>
        </div>
      )}

      <div className="space-y-2">
        <button onClick={onConfirm}
          className="w-full h-11 bg-blue-600 hover:bg-blue-700 text-white text-[13px] font-bold rounded-xl transition-colors shadow-sm">
          Save Activity
        </button>
        <button onClick={onBack}
          className="w-full h-9 text-[12px] font-semibold text-slate-500 hover:text-slate-700 transition-colors">
          ← Go back and edit
        </button>
      </div>
    </div>
  )
}

// ─── Done state ───────────────────────────────────────────────────────────────

function DoneStep({ action, vehicle, onClose, onAnother }: {
  action: ActionId; vehicle: FoundVehicle; onClose: () => void; onAnother: () => void
}) {
  const act = getAction(action)
  const needsVerification = ['recovr', 'mdd', 'tag'].includes(action)

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-5 py-8 gap-5">
      <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center">
        <span className="text-emerald-600 scale-125">{I.check}</span>
      </div>
      <div className="text-center">
        <h3 className="text-[18px] font-bold text-slate-900 mb-1">Activity Logged</h3>
        <p className="text-[13px] text-slate-500">
          <span className="font-semibold">{act.label}</span> recorded for{' '}
          <span className="font-bold text-slate-800">{vehicle.make} {vehicle.model}</span>
        </p>
        <p className="text-[12px] font-mono text-blue-600 mt-1">{vehicle.stock}</p>
      </div>

      {needsVerification ? (
        <div className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-4 py-2.5 text-center w-full">
          Queued for verification · Will confirm during next Inventory Sync
        </div>
      ) : (
        <div className="text-[11px] text-slate-400 bg-slate-50 border border-slate-100 rounded-lg px-4 py-2 text-center">
          Added to vehicle timeline · Syncing to LotSync cloud
        </div>
      )}

      <div className="flex flex-col gap-2 w-full">
        <button onClick={onAnother}
          className="w-full h-10 bg-blue-600 hover:bg-blue-700 text-white text-[13px] font-bold rounded-xl transition-colors">
          Log another activity
        </button>
        <button onClick={onClose}
          className="w-full h-10 bg-white hover:bg-slate-50 text-slate-700 text-[13px] font-semibold border border-slate-200 hover:border-slate-300 rounded-xl transition-colors">
          Done
        </button>
      </div>
    </div>
  )
}

// ─── Panel ────────────────────────────────────────────────────────────────────

function QuickLogPanel({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState<Step>('action')
  const [action, setAction] = useState<ActionId | null>(null)
  const [vehicle, setVehicle] = useState<FoundVehicle | null>(null)
  const [details, setDetails] = useState<DetailsState | null>(null)

  const reset = () => { setStep('action'); setAction(null); setVehicle(null); setDetails(null) }

  const handleBack = () => {
    if (step === 'vehicle') { setStep('action'); setAction(null) }
    else if (step === 'details') setStep('vehicle')
    else if (step === 'review') setStep('details')
    else if (step === 'done') reset()
  }

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 flex-shrink-0">
        <div className="flex items-center gap-3">
          {step !== 'action' && step !== 'done' && (
            <button onClick={handleBack}
              className="w-7 h-7 flex items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition-colors">
              {I.back}
            </button>
          )}
          <h2 className="text-[16px] font-bold text-slate-900">Log Activity</h2>
        </div>
        <button onClick={onClose}
          className="w-7 h-7 flex items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors">
          {I.close}
        </button>
      </div>

      {step !== 'done' && <StepIndicator current={step} action={action} />}

      {step === 'action' && <ActionStep onSelect={id => { setAction(id); setStep('vehicle') }} />}

      {step === 'vehicle' && (
        <VehicleStep onFound={v => setVehicle(v)} onContinue={v => { setVehicle(v); setStep('details') }} />
      )}

      {step === 'details' && action && vehicle && (
        <DetailsStep action={action} vehicle={vehicle} onNext={data => { setDetails(data); setStep('review') }} />
      )}

      {step === 'review' && action && vehicle && details && (
        <ReviewStep action={action} vehicle={vehicle} details={details}
          onConfirm={() => setStep('done')} onBack={() => setStep('details')} />
      )}

      {step === 'done' && action && vehicle && (
        <DoneStep action={action} vehicle={vehicle} onClose={onClose} onAnother={reset} />
      )}
    </div>
  )
}

// ─── FAB ─────────────────────────────────────────────────────────────────────

export default function QuickLog({ onVehicleSelect: _onVehicleSelect }: { onVehicleSelect?: (s: string) => void }) {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title="Log Activity"
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2.5 px-5 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-200 hover:-translate-y-0.5 group"
        style={{ height: '50px' }}>
        <span className="group-hover:rotate-90 transition-transform duration-200">{I.plus}</span>
        <span className="text-[14px] font-bold">Log Activity</span>
      </button>

      <div
        onClick={() => setOpen(false)}
        className="fixed inset-0 z-40 bg-black/20 backdrop-blur-[1px] transition-opacity duration-200"
        style={{ opacity: open ? 1 : 0, pointerEvents: open ? 'auto' : 'none' }}
      />

      <div
        className="fixed top-0 right-0 h-full z-50 bg-white shadow-2xl shadow-slate-900/20 transition-transform duration-300 ease-out flex flex-col"
        style={{ width: '480px', transform: open ? 'translateX(0)' : 'translateX(100%)' }}>
        {open && <QuickLogPanel onClose={() => setOpen(false)} />}
      </div>
    </>
  )
}
