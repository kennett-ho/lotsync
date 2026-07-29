import { useState } from 'react'

type AppRole = 'Lot Staff' | 'Lot Manager' | 'Tower Manager' | 'Controller' | 'Sales Manager' | 'Recon Manager' | 'Service Advisor' | 'Detail Team'

type TradeInStatus =
  | 'awaiting-stock'
  | 'awaiting-keys'
  | 'awaiting-recovr'
  | 'awaiting-zone'
  | 'ready'
  | 'completed'

type PurchaseType = 'customer-trade' | 'lease-return' | 'auction'

interface TradeIn {
  id: string
  vin: string
  stock?: string
  year: number
  make: string
  model: string
  trim?: string
  color: string
  mileage?: number
  purchaseType: PurchaseType
  status: TradeInStatus
  assignedTo?: string
  receivedDate?: string
  receivedLabel: string
  notes?: string
  timeline: { label: string; done: boolean; active?: boolean }[]
  auditFlags?: string[]
}

const statusCfg: Record<TradeInStatus, { label: string; dot: string; text: string; bg: string }> = {
  'awaiting-stock': { label: 'Awaiting Stock #',  dot: 'bg-slate-400',    text: 'text-slate-600',    bg: 'bg-slate-100' },
  'awaiting-keys':  { label: 'Awaiting Keys',     dot: 'bg-amber-400',   text: 'text-amber-700',   bg: 'bg-amber-50' },
  'awaiting-recovr':{ label: 'Awaiting RecovR',   dot: 'bg-blue-400',    text: 'text-blue-700',    bg: 'bg-blue-50' },
  'awaiting-zone':  { label: 'Awaiting Zone',     dot: 'bg-violet-400',  text: 'text-violet-700',  bg: 'bg-violet-50' },
  'ready':          { label: 'Inventory Ready',   dot: 'bg-emerald-400', text: 'text-emerald-700', bg: 'bg-emerald-50' },
  'completed':      { label: 'Completed',         dot: 'bg-emerald-500', text: 'text-emerald-800', bg: 'bg-emerald-100' },
}

function buildTimeline(status: TradeInStatus): { label: string; done: boolean; active?: boolean }[] {
  const steps = ['Stock Number', 'Keys', 'RecovR Installed', 'Zone Assigned', 'Inventory Ready']
  const order: TradeInStatus[] = ['awaiting-stock', 'awaiting-keys', 'awaiting-recovr', 'awaiting-zone', 'ready', 'completed']
  const idx = order.indexOf(status)
  return steps.map((label, i) => {
    if (status === 'completed') return { label, done: true }
    if (i < idx - 1) return { label, done: true }
    if (i === idx - 1) return { label, done: true }
    if (i === idx) return { label, done: false, active: true }
    return { label, done: false }
  })
}

const SEED_TRADES: TradeIn[] = [
  {
    id: 'ti1', vin: '1HGCV1F30NA012847', stock: 'TI-2024-0048',
    year: 2021, make: 'Honda', model: 'Accord', trim: 'Sport',
    color: 'Sonic Gray Pearl', mileage: 42180, purchaseType: 'customer-trade',
    status: 'ready', assignedTo: 'Marcus Torres',
    receivedDate: 'Today', receivedLabel: 'Today · 8:30 AM',
    notes: 'Minor scratch on rear bumper',
    timeline: buildTimeline('ready'),
  },
  {
    id: 'ti2', vin: '5YJSA1E26MF123456', stock: 'TI-2024-0047',
    year: 2020, make: 'Tesla', model: 'Model S', trim: 'Long Range',
    color: 'Midnight Silver', mileage: 38200, purchaseType: 'customer-trade',
    status: 'awaiting-zone', assignedTo: 'Marcus Torres',
    receivedLabel: 'Today · 9:14 AM',
    timeline: buildTimeline('awaiting-zone'),
  },
  {
    id: 'ti3', vin: '2T3RFREV0JW812345', stock: 'TI-2024-0046',
    year: 2018, make: 'Toyota', model: 'RAV4', trim: 'XLE',
    color: 'Magnetic Gray', mileage: 67440, purchaseType: 'lease-return',
    status: 'awaiting-recovr', assignedTo: undefined,
    receivedLabel: 'Today · 10:02 AM',
    timeline: buildTimeline('awaiting-recovr'),
  },
  {
    id: 'ti4', vin: '1FADP3F22JL234567', stock: undefined,
    year: 2018, make: 'Ford', model: 'Focus', trim: 'SE',
    color: 'Oxford White', mileage: 89100, purchaseType: 'customer-trade',
    status: 'awaiting-stock', assignedTo: undefined,
    receivedLabel: 'Today · 11:30 AM',
    timeline: buildTimeline('awaiting-stock'),
  },
  {
    id: 'ti5', vin: '3VW217AT8FM345678', stock: 'TI-2024-0045',
    year: 2019, make: 'Volkswagen', model: 'Jetta', trim: 'SEL',
    color: 'Deep Black Pearl', mileage: 51230, purchaseType: 'auction',
    status: 'awaiting-keys', assignedTo: 'K. Williams',
    receivedLabel: 'Yesterday · 4:15 PM',
    timeline: buildTimeline('awaiting-keys'),
  },
  {
    id: 'ti6', vin: '1G1ZD5ST4JF456789', stock: 'TI-2024-0044',
    year: 2018, make: 'Chevrolet', model: 'Malibu', trim: 'LT',
    color: 'Mosaic Black', mileage: 72890, purchaseType: 'customer-trade',
    status: 'completed', assignedTo: 'Marcus Torres',
    receivedLabel: 'Yesterday · 2:30 PM',
    timeline: buildTimeline('completed'),
  },
  {
    id: 'ti7', vin: '5NPE34AF5JH567890', stock: 'TI-2024-0043',
    year: 2018, make: 'Hyundai', model: 'Sonata', trim: 'SEL',
    color: 'Quartz White', mileage: 58340, purchaseType: 'customer-trade',
    status: 'completed', assignedTo: 'K. Williams',
    receivedLabel: '2 days ago',
    timeline: buildTimeline('completed'),
  },
  {
    id: 'ti8', vin: '1C4RJFBG4JC678901', stock: undefined,
    year: 2018, make: 'Jeep', model: 'Grand Cherokee', trim: 'Laredo',
    color: 'Granite Crystal', mileage: 94200, purchaseType: 'customer-trade',
    status: 'awaiting-stock', assignedTo: undefined,
    receivedLabel: 'Today · 7:45 AM',
    auditFlags: ['No stock number assigned', 'Missing mileage confirmation'],
    timeline: buildTimeline('awaiting-stock'),
  },
]

const STAFF_OPTIONS = ['Marcus Torres', 'K. Williams', 'J. Ramirez']

const purchaseTypeCfg: Record<PurchaseType, { label: string; text: string; bg: string }> = {
  'customer-trade': { label: 'Trade-In',     text: 'text-slate-600', bg: 'bg-slate-100' },
  'lease-return':   { label: 'Lease Return', text: 'text-blue-700',  bg: 'bg-blue-50' },
  'auction':        { label: 'Auction',      text: 'text-orange-700',bg: 'bg-orange-50' },
}

function StatusPill({ status }: { status: TradeInStatus }) {
  const cfg = statusCfg[status]
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-semibold ${cfg.bg} ${cfg.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  )
}

function TimelineCard({ timeline }: { timeline: { label: string; done: boolean; active?: boolean }[] }) {
  return (
    <div className="bg-white rounded-xl border border-slate-100 p-4">
      <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-3">Progress</p>
      <div className="flex items-start">
        {timeline.map((step, i) => (
          <div key={step.label} className="flex-1 flex flex-col items-center">
            <div className="flex items-center w-full">
              {i > 0 && (
                <div className={`flex-1 h-0.5 ${step.done ? 'bg-emerald-400' : 'bg-slate-200'}`} />
              )}
              <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
                step.done
                  ? 'bg-emerald-400'
                  : step.active
                  ? 'bg-blue-500 ring-2 ring-blue-200'
                  : 'bg-slate-200'
              }`}>
                {step.done ? (
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : step.active ? (
                  <span className="w-2 h-2 rounded-full bg-white" />
                ) : (
                  <span className="w-2 h-2 rounded-full bg-slate-300" />
                )}
              </div>
              {i < timeline.length - 1 && (
                <div className={`flex-1 h-0.5 ${timeline[i + 1]?.done ? 'bg-emerald-400' : 'bg-slate-200'}`} />
              )}
            </div>
            <p className={`text-[9px] text-center mt-1.5 leading-tight px-0.5 ${
              step.done ? 'text-emerald-600 font-medium' : step.active ? 'text-blue-600 font-semibold' : 'text-slate-400'
            }`}>
              {step.label}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

function VehicleCard({ trade }: { trade: TradeIn }) {
  const ptCfg = purchaseTypeCfg[trade.purchaseType]
  return (
    <div className="bg-white rounded-xl border border-slate-100 p-4">
      <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-3">Vehicle Information</p>
      <div className="grid grid-cols-2 gap-x-6 gap-y-2">
        <div>
          <p className="text-[10px] text-slate-400">VIN</p>
          <p className="text-[11px] font-mono text-slate-800">{trade.vin}</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-400">Stock #</p>
          {trade.stock
            ? <p className="text-[11px] font-mono text-blue-600 font-semibold">{trade.stock}</p>
            : <p className="text-[11px] text-amber-600 font-medium">Not Assigned</p>
          }
        </div>
        <div>
          <p className="text-[10px] text-slate-400">Vehicle</p>
          <p className="text-[11px] text-slate-800 font-medium">{trade.year} {trade.make} {trade.model}{trade.trim ? ` ${trade.trim}` : ''}</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-400">Color</p>
          <p className="text-[11px] text-slate-700">{trade.color}</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-400">Mileage</p>
          <p className="text-[11px] text-slate-700">{trade.mileage != null ? trade.mileage.toLocaleString() + ' mi' : '—'}</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-400">Purchase Type</p>
          <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] font-semibold ${ptCfg.bg} ${ptCfg.text}`}>
            {ptCfg.label}
          </span>
        </div>
        <div>
          <p className="text-[10px] text-slate-400">Received</p>
          <p className="text-[11px] text-slate-700">{trade.receivedLabel}</p>
        </div>
        {trade.notes && (
          <div className="col-span-2">
            <p className="text-[10px] text-slate-400">Notes</p>
            <p className="text-[11px] text-slate-600">{trade.notes}</p>
          </div>
        )}
      </div>
    </div>
  )
}

function LotStaffDetail({
  trade,
  effectiveStatus,
  onStatusChange,
  showZoneInput,
  setShowZoneInput,
  zoneValue,
  setZoneValue,
}: {
  trade: TradeIn
  effectiveStatus: TradeInStatus
  onStatusChange: (id: string, s: TradeInStatus) => void
  showZoneInput: string | null
  setShowZoneInput: (v: string | null) => void
  zoneValue: string
  setZoneValue: (v: string) => void
}) {
  return (
    <div className="space-y-3">
      <VehicleCard trade={trade} />
      <TimelineCard timeline={trade.timeline} />
      <div className="bg-white rounded-xl border border-slate-100 p-4">
        <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-3">Actions</p>
        {effectiveStatus === 'awaiting-stock' && (
          <div className="flex items-start gap-2 p-3 bg-amber-50 rounded-lg border border-amber-100">
            <svg className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
            <p className="text-[11px] text-amber-700">Awaiting stock number assignment from management.</p>
          </div>
        )}
        {effectiveStatus === 'awaiting-keys' && (
          <button
            onClick={() => onStatusChange(trade.id, 'awaiting-recovr')}
            className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white text-[12px] font-semibold rounded-lg transition-colors"
          >
            Mark Keys Received
          </button>
        )}
        {effectiveStatus === 'awaiting-recovr' && (
          <button
            onClick={() => onStatusChange(trade.id, 'awaiting-zone')}
            className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white text-[12px] font-semibold rounded-lg transition-colors"
          >
            Mark RecovR Installed
          </button>
        )}
        {effectiveStatus === 'awaiting-zone' && (
          <div className="space-y-2">
            {showZoneInput === trade.id ? (
              <div className="flex gap-2">
                <input
                  className="flex-1 border border-slate-200 rounded-lg px-2 py-1.5 text-[12px] focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="Zone (e.g. B-12)"
                  value={zoneValue}
                  onChange={e => setZoneValue(e.target.value)}
                  autoFocus
                />
                <button
                  onClick={() => {
                    if (zoneValue.trim()) {
                      onStatusChange(trade.id, 'ready')
                      setShowZoneInput(null)
                      setZoneValue('')
                    }
                  }}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-semibold rounded-lg transition-colors"
                >
                  Save
                </button>
                <button
                  onClick={() => { setShowZoneInput(null); setZoneValue('') }}
                  className="px-2 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 text-[11px] rounded-lg transition-colors"
                >
                  ✕
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowZoneInput(trade.id)}
                className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white text-[12px] font-semibold rounded-lg transition-colors"
              >
                Assign Parking Zone
              </button>
            )}
          </div>
        )}
        {effectiveStatus === 'ready' && (
          <button
            onClick={() => onStatusChange(trade.id, 'completed')}
            className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-[12px] font-semibold rounded-lg transition-colors"
          >
            Confirm Inventory Ready
          </button>
        )}
        {effectiveStatus === 'completed' && (
          <div className="flex items-center gap-2 text-emerald-700">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            <span className="text-[12px] font-semibold">Completed</span>
          </div>
        )}
      </div>
    </div>
  )
}

function LotManagerDetail({
  trade,
  assignOverrides,
  onAssign,
}: {
  trade: TradeIn
  assignOverrides: Record<string, string>
  onAssign: (id: string, name: string) => void
}) {
  const [showDropdown, setShowDropdown] = useState(false)
  const effectiveAssignee = assignOverrides[trade.id] ?? trade.assignedTo

  return (
    <div className="space-y-3">
      <VehicleCard trade={trade} />
      <TimelineCard timeline={trade.timeline} />
      <div className="bg-white rounded-xl border border-slate-100 p-4">
        <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-3">Assignment</p>
        {effectiveAssignee ? (
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center">
              <span className="text-[10px] font-bold text-blue-700">
                {effectiveAssignee.split(' ').map((n: string) => n[0]).join('')}
              </span>
            </div>
            <span className="text-[12px] text-slate-700 font-medium">{effectiveAssignee}</span>
            <button
              onClick={() => setShowDropdown(v => !v)}
              className="ml-auto text-[10px] text-blue-600 hover:underline"
            >
              Reassign
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-[12px] text-slate-400">Unassigned</span>
            <button
              onClick={() => setShowDropdown(v => !v)}
              className="ml-auto px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white text-[10px] font-semibold rounded-lg transition-colors"
            >
              Assign Staff
            </button>
          </div>
        )}
        {showDropdown && (
          <div className="mt-2 border border-slate-200 rounded-lg overflow-hidden shadow-sm">
            {STAFF_OPTIONS.map(name => (
              <button
                key={name}
                onClick={() => { onAssign(trade.id, name); setShowDropdown(false) }}
                className="w-full text-left px-3 py-2 text-[11px] text-slate-700 hover:bg-blue-50 border-b border-slate-100 last:border-0 transition-colors"
              >
                {name}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function TowerManagerDetail({ trade }: { trade: TradeIn }) {
  const s = trade.status
  let bucket: { label: string; text: string; bg: string; border: string }
  if (s === 'awaiting-stock' || s === 'awaiting-keys') {
    bucket = { label: 'Awaiting Intake', text: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200' }
  } else if (s === 'awaiting-recovr' || s === 'awaiting-zone') {
    bucket = { label: 'In Preparation', text: 'text-blue-700', bg: 'bg-blue-50', border: 'border-blue-200' }
  } else {
    bucket = { label: 'Inventory Ready', text: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-200' }
  }

  return (
    <div className="space-y-3">
      <div className={`${bucket.bg} border ${bucket.border} rounded-xl p-3 flex items-center justify-between`}>
        <span className={`text-[12px] font-semibold ${bucket.text}`}>{bucket.label}</span>
        <span className={`text-[10px] ${bucket.text}`}>{statusCfg[s].label}</span>
      </div>
      <VehicleCard trade={trade} />
      <TimelineCard timeline={trade.timeline} />
    </div>
  )
}

function SalesManagerDetail({ trade }: { trade: TradeIn }) {
  const s = trade.status
  let simplified: { label: string; text: string; bg: string }
  if (s === 'awaiting-stock' || s === 'awaiting-keys') {
    simplified = { label: 'Received', text: 'text-slate-700', bg: 'bg-slate-100' }
  } else if (s === 'awaiting-recovr' || s === 'awaiting-zone') {
    simplified = { label: 'Awaiting Inventory', text: 'text-blue-700', bg: 'bg-blue-50' }
  } else {
    simplified = { label: 'Inventory Ready', text: 'text-emerald-700', bg: 'bg-emerald-50' }
  }

  return (
    <div className="space-y-3">
      <div className={`${simplified.bg} rounded-xl p-3`}>
        <span className={`text-[12px] font-semibold ${simplified.text}`}>{simplified.label}</span>
      </div>
      <VehicleCard trade={trade} />
    </div>
  )
}

function ControllerDetail({ trade }: { trade: TradeIn }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 p-3 bg-slate-100 rounded-xl border border-slate-200">
        <svg className="w-4 h-4 text-slate-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
        <span className="text-[11px] font-semibold text-slate-600">Audit View — Read Only</span>
      </div>
      <div className="bg-white rounded-xl border border-slate-100 p-4">
        <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-3">Audit Details</p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2">
          <div>
            <p className="text-[10px] text-slate-400">VIN</p>
            <p className="text-[11px] font-mono text-slate-800">{trade.vin}</p>
          </div>
          <div>
            <p className="text-[10px] text-slate-400">Stock #</p>
            {trade.stock
              ? <p className="text-[11px] font-mono text-blue-600">{trade.stock}</p>
              : <p className="text-[11px] text-amber-600">Not Assigned</p>
            }
          </div>
          <div>
            <p className="text-[10px] text-slate-400">Status</p>
            <StatusPill status={trade.status} />
          </div>
        </div>
        {trade.auditFlags && trade.auditFlags.length > 0 && (
          <div className="mt-3">
            <p className="text-[10px] text-slate-400 mb-1.5">Audit Flags</p>
            <div className="flex flex-wrap gap-1.5">
              {trade.auditFlags.map(flag => (
                <span key={flag} className="inline-block px-2 py-0.5 bg-amber-50 border border-amber-200 text-amber-700 text-[10px] font-medium rounded-full">
                  ⚠ {flag}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
      <div className="bg-white rounded-xl border border-slate-100 p-4">
        <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-2">Audit History</p>
        <p className="text-[11px] text-slate-400 italic">No audit events recorded.</p>
      </div>
    </div>
  )
}

function NewTradeInForm({
  onClose,
  onCreate,
}: {
  onClose: () => void
  onCreate: (trade: TradeIn) => void
}) {
  const [vinInput, setVinInput] = useState('')
  const [decoded, setDecoded] = useState(false)
  const [stockInput, setStockInput] = useState('')
  const [colorInput, setColorInput] = useState('')
  const [mileageInput, setMileageInput] = useState('')
  const [purchaseType, setPurchaseType] = useState<PurchaseType>('customer-trade')
  const [notes, setNotes] = useState('')
  const [trim, setTrim] = useState('EX-L')
  const [engine, setEngine] = useState('1.5L Turbo 4-cyl')

  const handleCreate = () => {
    const id = 'ti-local-' + Date.now()
    const newTrade: TradeIn = {
      id,
      vin: vinInput || '1HGCV2F59NA000000',
      stock: stockInput || undefined,
      year: 2022,
      make: 'Honda',
      model: 'CR-V',
      trim,
      color: colorInput || 'Unknown',
      mileage: mileageInput ? parseInt(mileageInput, 10) : undefined,
      purchaseType,
      status: 'awaiting-stock',
      receivedLabel: 'Just now',
      notes: notes || undefined,
      timeline: buildTimeline('awaiting-stock'),
    }
    onCreate(newTrade)
  }

  return (
    <div className="h-full flex flex-col bg-white rounded-xl border border-slate-100">
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
        <h2 className="text-[14px] font-bold text-slate-800">New Trade-In</h2>
        <button onClick={onClose} className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 transition-colors">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        <div>
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-3">Vehicle Information</p>
          <div className="space-y-3">
            <div>
              <label className="block text-[11px] text-slate-500 mb-1">VIN</label>
              <div className="flex gap-2">
                <input
                  className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-[12px] font-mono focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="17-character VIN"
                  value={vinInput}
                  onChange={e => setVinInput(e.target.value)}
                />
                <button
                  onClick={() => setDecoded(true)}
                  className="px-3 py-2 bg-slate-700 hover:bg-slate-800 text-white text-[11px] font-semibold rounded-lg transition-colors whitespace-nowrap"
                >
                  Decode
                </button>
              </div>
              {decoded && (
                <div className="mt-1.5 flex items-center gap-1.5">
                  <svg className="w-3.5 h-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-[10px] text-emerald-600 font-semibold">VIN Decoded</span>
                </div>
              )}
            </div>

            {decoded && (
              <div className="space-y-3 p-3 bg-slate-50 rounded-lg border border-slate-100">
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="block text-[10px] text-slate-400 mb-0.5">Year</label>
                    <input className="w-full border border-slate-200 rounded-lg px-2 py-1.5 text-[12px] focus:outline-none bg-white text-slate-500" defaultValue="2022" readOnly />
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-400 mb-0.5">Make</label>
                    <input className="w-full border border-slate-200 rounded-lg px-2 py-1.5 text-[12px] focus:outline-none bg-white text-slate-500" defaultValue="Honda" readOnly />
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-400 mb-0.5">Model</label>
                    <input className="w-full border border-slate-200 rounded-lg px-2 py-1.5 text-[12px] focus:outline-none bg-white text-slate-500" defaultValue="CR-V" readOnly />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[10px] text-slate-400 mb-0.5">Trim</label>
                    <input
                      className="w-full border border-slate-200 rounded-lg px-2 py-1.5 text-[12px] focus:outline-none focus:ring-2 focus:ring-blue-300 bg-white"
                      value={trim}
                      onChange={e => setTrim(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-400 mb-0.5">Engine</label>
                    <input
                      className="w-full border border-slate-200 rounded-lg px-2 py-1.5 text-[12px] focus:outline-none focus:ring-2 focus:ring-blue-300 bg-white"
                      value={engine}
                      onChange={e => setEngine(e.target.value)}
                    />
                  </div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] text-slate-500 mb-1">Stock Number <span className="text-slate-300">(optional)</span></label>
                <input
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-[12px] focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="TI-2024-XXXX"
                  value={stockInput}
                  onChange={e => setStockInput(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-[11px] text-slate-500 mb-1">Exterior Color</label>
                <input
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-[12px] focus:outline-none focus:ring-2 focus:ring-blue-300"
                  placeholder="e.g. Sonic Gray Pearl"
                  value={colorInput}
                  onChange={e => setColorInput(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] text-slate-500 mb-1">Mileage <span className="text-slate-300">(optional)</span></label>
              <input
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-[12px] focus:outline-none focus:ring-2 focus:ring-blue-300"
                placeholder="e.g. 42000"
                type="number"
                value={mileageInput}
                onChange={e => setMileageInput(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div>
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-3">Purchase Details</p>
          <div className="space-y-3">
            <div>
              <label className="block text-[11px] text-slate-500 mb-2">Purchase Type</label>
              <div className="flex gap-2 flex-wrap">
                {(['customer-trade', 'lease-return', 'auction'] as PurchaseType[]).map(pt => (
                  <button
                    key={pt}
                    onClick={() => setPurchaseType(pt)}
                    className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold border transition-colors ${
                      purchaseType === pt
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-slate-600 border-slate-200 hover:border-blue-300'
                    }`}
                  >
                    {purchaseTypeCfg[pt].label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-[11px] text-slate-500 mb-1">Manager Notes</label>
              <textarea
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-[12px] focus:outline-none focus:ring-2 focus:ring-blue-300 resize-none"
                rows={3}
                placeholder="Any notes about this trade-in..."
                value={notes}
                onChange={e => setNotes(e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="px-5 py-4 border-t border-slate-100 flex gap-2">
        <button
          onClick={handleCreate}
          className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-[12px] font-semibold rounded-lg transition-colors"
        >
          Create Trade-In
        </button>
        <button
          onClick={onClose}
          className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 text-[12px] font-semibold rounded-lg transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

export default function TradeIns({ role }: { role: AppRole }): JSX.Element {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [filter, setFilter] = useState<TradeInStatus | 'all'>('all')
  const [search, setSearch] = useState('')
  const [statusOverrides, setStatusOverrides] = useState<Record<string, TradeInStatus>>({})
  const [assignOverrides, setAssignOverrides] = useState<Record<string, string>>({})
  const [showCreate, setShowCreate] = useState(false)
  const [localTrades, setLocalTrades] = useState<TradeIn[]>([])
  const [showZoneInput, setShowZoneInput] = useState<string | null>(null)
  const [zoneValue, setZoneValue] = useState('')

  const canCreate = role === 'Sales Manager' || role === 'Tower Manager'
  const allTrades = [...SEED_TRADES, ...localTrades]

  const effectiveStatus = (t: TradeIn): TradeInStatus => statusOverrides[t.id] ?? t.status

  const filtered = allTrades.filter(t => {
    if (filter !== 'all' && effectiveStatus(t) !== filter) return false
    if (search) {
      const q = search.toLowerCase()
      return (
        t.vin.toLowerCase().includes(q) ||
        (t.stock ?? '').toLowerCase().includes(q) ||
        t.make.toLowerCase().includes(q) ||
        t.model.toLowerCase().includes(q)
      )
    }
    return true
  })

  const counts = allTrades.reduce<Record<string, number>>((acc, t) => {
    const s = effectiveStatus(t)
    acc[s] = (acc[s] ?? 0) + 1
    return acc
  }, {})

  const filterOptions: { key: TradeInStatus | 'all'; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'awaiting-stock', label: 'Awaiting Stock #' },
    { key: 'awaiting-keys', label: 'Awaiting Keys' },
    { key: 'awaiting-recovr', label: 'Awaiting RecovR' },
    { key: 'awaiting-zone', label: 'Awaiting Zone' },
    { key: 'ready', label: 'Inventory Ready' },
    { key: 'completed', label: 'Completed' },
  ]

  const selected = allTrades.find(t => t.id === selectedId) ?? null

  const handleStatusChange = (id: string, s: TradeInStatus) => {
    setStatusOverrides(prev => ({ ...prev, [id]: s }))
  }

  const handleAssign = (id: string, name: string) => {
    setAssignOverrides(prev => ({ ...prev, [id]: name }))
  }

  const handleCreate = (trade: TradeIn) => {
    setLocalTrades(prev => [trade, ...prev])
    setShowCreate(false)
    setSelectedId(trade.id)
  }

  // Build effective trade for detail (with overridden status reflected in timeline)
  const effectiveTrade = selected
    ? { ...selected, status: effectiveStatus(selected) }
    : null

  return (
    <div className="flex h-full bg-slate-50 overflow-hidden">
      {/* Left Sidebar */}
      <div className="w-44 shrink-0 bg-white border-r border-slate-100 flex flex-col py-3 px-2 gap-0.5">
        {canCreate && (
          <button
            onClick={() => { setShowCreate(true); setSelectedId(null) }}
            className="w-full mb-2 py-2 bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            New Trade-In
          </button>
        )}
        <p className="text-[9px] font-semibold text-slate-400 uppercase tracking-wide px-2 mb-1">Status Filter</p>
        {filterOptions.map(opt => {
          const count = opt.key === 'all' ? allTrades.length : (counts[opt.key] ?? 0)
          const isActive = filter === opt.key
          return (
            <button
              key={opt.key}
              onClick={() => setFilter(opt.key)}
              className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-left transition-colors ${
                isActive ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <span className="text-[11px] font-medium truncate">{opt.label}</span>
              {count > 0 && (
                <span className={`text-[9px] font-bold rounded-full px-1.5 py-0.5 ml-1 shrink-0 ${
                  isActive ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500'
                }`}>
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Center List */}
      <div className="shrink-0 bg-white border-r border-slate-100 flex flex-col" style={{ width: 'clamp(220px, 22vw, 290px)' }}>
        <div className="px-3 pt-3 pb-2 border-b border-slate-100">
          <div className="relative">
            <svg className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <circle cx={11} cy={11} r={8} />
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35" />
            </svg>
            <input
              className="w-full pl-7 pr-2 py-1.5 text-[11px] border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
              placeholder="Search VIN, stock, make…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {filtered.length === 0 && (
            <div className="py-8 text-center text-[11px] text-slate-400">No trade-ins found</div>
          )}
          {filtered.map(t => {
            const es = effectiveStatus(t)
            const ptCfg = purchaseTypeCfg[t.purchaseType]
            const isSelected = selectedId === t.id
            return (
              <button
                key={t.id}
                onClick={() => { setSelectedId(t.id); setShowCreate(false) }}
                className={`w-full text-left px-3 py-2.5 border-b border-slate-100 transition-colors ${
                  isSelected ? 'bg-blue-50' : 'hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-[12px] font-bold text-slate-800 truncate mr-1">
                    {t.year} {t.make} {t.model}
                  </span>
                  <StatusPill status={es} />
                </div>
                <div className="flex items-center justify-between mb-0.5">
                  {t.stock
                    ? <span className="text-[10px] font-mono text-blue-600 font-semibold">{t.stock}</span>
                    : <span className="text-[10px] text-amber-600 font-medium">No Stock #</span>
                  }
                  <span className="text-[10px] text-slate-400">{t.receivedLabel}</span>
                </div>
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-[10px] text-slate-400">{t.color}</span>
                  <span className="text-slate-200">·</span>
                  <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${ptCfg.bg} ${ptCfg.text}`}>
                    {ptCfg.label}
                  </span>
                  {t.mileage != null && (
                    <>
                      <span className="text-slate-200">·</span>
                      <span className="text-[10px] text-slate-400">{t.mileage.toLocaleString()} mi</span>
                    </>
                  )}
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Right Detail */}
      <div className="flex-1 overflow-y-auto p-4">
        {showCreate && canCreate ? (
          <NewTradeInForm onClose={() => setShowCreate(false)} onCreate={handleCreate} />
        ) : effectiveTrade ? (
          <div className="space-y-3 max-w-2xl">
            <div className="flex items-start justify-between mb-1">
              <div>
                <h2 className="text-[16px] font-bold text-slate-800">
                  {effectiveTrade.year} {effectiveTrade.make} {effectiveTrade.model}{effectiveTrade.trim ? ` ${effectiveTrade.trim}` : ''}
                </h2>
                <p className="text-[11px] text-slate-400 mt-0.5">{effectiveTrade.receivedLabel}</p>
              </div>
              <StatusPill status={effectiveTrade.status} />
            </div>

            {role === 'Lot Staff' && (
              <LotStaffDetail
                trade={effectiveTrade}
                effectiveStatus={effectiveTrade.status}
                onStatusChange={handleStatusChange}
                showZoneInput={showZoneInput}
                setShowZoneInput={setShowZoneInput}
                zoneValue={zoneValue}
                setZoneValue={setZoneValue}
              />
            )}
            {role === 'Lot Manager' && (
              <LotManagerDetail
                trade={effectiveTrade}
                assignOverrides={assignOverrides}
                onAssign={handleAssign}
              />
            )}
            {role === 'Tower Manager' && (
              <TowerManagerDetail trade={effectiveTrade} />
            )}
            {role === 'Sales Manager' && (
              <SalesManagerDetail trade={effectiveTrade} />
            )}
            {role === 'Controller' && (
              <ControllerDetail trade={effectiveTrade} />
            )}
            {(role === 'Recon Manager' || role === 'Service Advisor' || role === 'Detail Team') && (
              <div className="space-y-3">
                <VehicleCard trade={effectiveTrade} />
                <TimelineCard timeline={effectiveTrade.timeline} />
              </div>
            )}
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center mb-3">
              <svg className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
              </svg>
            </div>
            <p className="text-[13px] font-semibold text-slate-600 mb-1">No trade-in selected</p>
            <p className="text-[11px] text-slate-400">Select a vehicle from the list to view details</p>
            {canCreate && (
              <button
                onClick={() => setShowCreate(true)}
                className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-[12px] font-semibold rounded-lg transition-colors"
              >
                + New Trade-In
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
