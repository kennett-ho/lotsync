// Transportation.tsx — Unified Dealer Trades + Customer Deliveries page

import { useState, useMemo } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

type AppRole = 'Lot Staff' | 'Lot Manager' | 'Tower Manager' | 'Controller' | 'Sales Manager' | 'Recon Manager' | 'Service Advisor' | 'Detail Team'

type TradeStatus = 'awaiting-pickup' | 'in-transit' | 'returned' | 'completed' | 'cancelled'
type TradePriority = 'urgent' | 'normal' | 'low'
type DelivStatus = 'scheduled' | 'assigned' | 'en-route' | 'delivered' | 'cancelled'

interface DealerTrade {
  id: string
  tradeNumber: string
  status: TradeStatus
  priority: TradePriority
  origin: { name: string; city: string; state: string }
  destination: { name: string; city: string; state: string }
  assignedDriver?: string
  etaLabel?: string
  vehicles: { stock: string; year: number; make: string; model: string; direction: 'in' | 'out' }[]
  updatedLabel: string
}

interface CustomerDelivery {
  id: string
  deliveryNumber: string
  status: DelivStatus
  priority: 'urgent' | 'normal'
  customer: { name: string; phone: string }
  vehicle: { stock: string; year: number; make: string; model: string; color: string }
  deliveryAddress: string
  scheduledTime: string
  assignedDriver?: string
  etaLabel?: string
  notes?: string
  updatedLabel: string
}

// ─── Status maps ──────────────────────────────────────────────────────────────

const tradeStat: Record<TradeStatus, { dot: string; text: string; label: string }> = {
  'awaiting-pickup': { dot: 'bg-blue-400',    text: 'text-blue-700',    label: 'Awaiting Pickup' },
  'in-transit':      { dot: 'bg-amber-400',   text: 'text-amber-700',   label: 'In Transit' },
  'returned':        { dot: 'bg-violet-400',  text: 'text-violet-700',  label: 'Returned' },
  'completed':       { dot: 'bg-emerald-400', text: 'text-emerald-700', label: 'Completed' },
  'cancelled':       { dot: 'bg-slate-300',   text: 'text-slate-400',   label: 'Cancelled' },
}

const delivStat: Record<DelivStatus, { dot: string; text: string; label: string }> = {
  'scheduled': { dot: 'bg-blue-400',    text: 'text-blue-700',    label: 'Scheduled' },
  'assigned':  { dot: 'bg-amber-400',   text: 'text-amber-700',   label: 'Assigned' },
  'en-route':  { dot: 'bg-violet-400',  text: 'text-violet-700',  label: 'En Route' },
  'delivered': { dot: 'bg-emerald-400', text: 'text-emerald-700', label: 'Delivered' },
  'cancelled': { dot: 'bg-slate-300',   text: 'text-slate-400',   label: 'Cancelled' },
}

// ─── Sample data ──────────────────────────────────────────────────────────────

const TRADES: DealerTrade[] = [
  {
    id: 't1', tradeNumber: 'DT-2024-0142', status: 'awaiting-pickup', priority: 'urgent',
    origin: { name: 'AutoNation BMW', city: 'Anaheim', state: 'CA' },
    destination: { name: 'Sunrise Honda', city: 'Buena Park', state: 'CA' },
    assignedDriver: 'Jordan Davis', etaLabel: 'ETA 11:30 AM',
    vehicles: [
      { stock: 'H72840', year: 2023, make: 'Subaru', model: 'Outback', direction: 'out' },
      { stock: 'G19283', year: 2022, make: 'Toyota', model: 'RAV4', direction: 'out' },
    ],
    updatedLabel: '9 min ago',
  },
  {
    id: 't2', tradeNumber: 'DT-2024-0141', status: 'in-transit', priority: 'normal',
    origin: { name: 'Sunrise Honda', city: 'Buena Park', state: 'CA' },
    destination: { name: 'Here', city: 'Anaheim', state: 'CA' },
    assignedDriver: 'K. Williams', etaLabel: 'ETA 2:15 PM',
    vehicles: [
      { stock: 'B29100', year: 2023, make: 'Honda', model: 'Civic', direction: 'in' },
    ],
    updatedLabel: '1h ago',
  },
  {
    id: 't3', tradeNumber: 'DT-2024-0140', status: 'awaiting-pickup', priority: 'normal',
    origin: { name: 'Here', city: 'Anaheim', state: 'CA' },
    destination: { name: 'CarMax Anaheim', city: 'Anaheim', state: 'CA' },
    vehicles: [
      { stock: 'D72044', year: 2024, make: 'Kia', model: 'Telluride', direction: 'out' },
    ],
    updatedLabel: '2h ago',
  },
  {
    id: 't4', tradeNumber: 'DT-2024-0139', status: 'returned', priority: 'normal',
    origin: { name: 'DCH Toyota', city: 'Torrance', state: 'CA' },
    destination: { name: 'Here', city: 'Anaheim', state: 'CA' },
    assignedDriver: 'Marcus Torres',
    vehicles: [
      { stock: 'A48291', year: 2023, make: 'Honda', model: 'Accord', direction: 'in' },
    ],
    updatedLabel: 'Yesterday',
  },
  {
    id: 't5', tradeNumber: 'DT-2024-0138', status: 'completed', priority: 'normal',
    origin: { name: 'AutoNation BMW', city: 'Anaheim', state: 'CA' },
    destination: { name: 'Here', city: 'Anaheim', state: 'CA' },
    assignedDriver: 'Marcus Torres',
    vehicles: [
      { stock: 'F92011', year: 2024, make: 'BMW', model: '5 Series', direction: 'in' },
    ],
    updatedLabel: 'Yesterday',
  },
  {
    id: 't6', tradeNumber: 'DT-2024-0137', status: 'cancelled', priority: 'low',
    origin: { name: 'Sunrise Honda', city: 'Buena Park', state: 'CA' },
    destination: { name: 'Here', city: 'Anaheim', state: 'CA' },
    vehicles: [
      { stock: 'C10029', year: 2022, make: 'Honda', model: 'Pilot', direction: 'in' },
    ],
    updatedLabel: '2 days ago',
  },
]

const DELIVERIES: CustomerDelivery[] = [
  {
    id: 'd1', deliveryNumber: 'DEL-2024-0091', status: 'scheduled', priority: 'urgent',
    customer: { name: 'James Okafor', phone: '(714) 555-0192' },
    vehicle: { stock: 'B93021', year: 2024, make: 'Toyota', model: 'Camry', color: 'Midnight Black' },
    deliveryAddress: '2847 Harbor Blvd, Costa Mesa, CA',
    scheduledTime: 'Today 1:45 PM',
    updatedLabel: '1h ago',
  },
  {
    id: 'd2', deliveryNumber: 'DEL-2024-0090', status: 'assigned', priority: 'normal',
    customer: { name: 'Maria Santos', phone: '(714) 555-0284' },
    vehicle: { stock: 'A48290', year: 2022, make: 'Honda', model: 'Civic', color: 'Rallye Red' },
    deliveryAddress: '1200 S State College Blvd, Anaheim CA',
    scheduledTime: 'Today 3:00 PM',
    assignedDriver: 'Marcus Torres', etaLabel: 'On time',
    updatedLabel: '45 min ago',
  },
  {
    id: 'd3', deliveryNumber: 'DEL-2024-0089', status: 'en-route', priority: 'normal',
    customer: { name: 'David Kim', phone: '(714) 555-0331' },
    vehicle: { stock: 'E51389', year: 2023, make: 'BMW', model: '3 Series', color: 'Black Sapphire' },
    deliveryAddress: '800 W Katella Ave, Orange CA',
    scheduledTime: 'Today 11:00 AM',
    assignedDriver: 'K. Williams', etaLabel: 'ETA 11:15 AM',
    updatedLabel: '22 min ago',
  },
  {
    id: 'd4', deliveryNumber: 'DEL-2024-0088', status: 'delivered', priority: 'normal',
    customer: { name: 'Robert Chen', phone: '(714) 555-0412' },
    vehicle: { stock: 'J72310', year: 2023, make: 'Toyota', model: 'RAV4', color: 'Magnetic Gray' },
    deliveryAddress: '441 N Tustin Ave, Orange CA',
    scheduledTime: 'Yesterday 2:00 PM',
    assignedDriver: 'Jordan Davis',
    updatedLabel: 'Yesterday',
  },
  {
    id: 'd5', deliveryNumber: 'DEL-2024-0087', status: 'cancelled', priority: 'normal',
    customer: { name: 'Amanda Torres', phone: '(714) 555-0589' },
    vehicle: { stock: 'K10082', year: 2024, make: 'Kia', model: 'Sportage', color: 'Snow White Pearl' },
    deliveryAddress: '2100 E Lincoln Ave, Anaheim CA',
    scheduledTime: 'Yesterday 4:00 PM',
    updatedLabel: '2 days ago',
  },
]

const DEALERS = ['AutoNation BMW', 'Sunrise Honda', 'CarMax Anaheim', 'DCH Toyota']

// ─── Icons ────────────────────────────────────────────────────────────────────

function IconTruck() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <rect x="1" y="3" width="15" height="13" rx="1"/><path d="M16 8h4l3 5v4h-7V8Z"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>
    </svg>
  )
}

function IconCar() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <path d="M5 17H3a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v9a2 2 0 0 1-2 2h-2"/><circle cx="7.5" cy="17.5" r="2.5"/><circle cx="16.5" cy="17.5" r="2.5"/>
    </svg>
  )
}

function IconUser() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
    </svg>
  )
}

function IconPhone() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2A19.79 19.79 0 0 1 3.08 4.18 2 2 0 0 1 5.06 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L9.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92Z"/>
    </svg>
  )
}

function IconMapPin() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0Z"/><circle cx="12" cy="10" r="3"/>
    </svg>
  )
}

function IconClock() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
    </svg>
  )
}

function IconArrowRight() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3 h-3">
      <path d="M5 12h14M12 5l7 7-7 7"/>
    </svg>
  )
}

function IconPlus() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <path d="M12 5v14M5 12h14"/>
    </svg>
  )
}

function IconX() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
      <path d="M18 6 6 18M6 6l12 12"/>
    </svg>
  )
}

function IconLock() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 text-slate-400">
      <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  )
}

function IconCheck() {
  return (
    <svg viewBox="0 0 12 12" fill="none" className="w-3 h-3">
      <path d="M2 6l3 3 5-5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

// ─── Shared sub-components ────────────────────────────────────────────────────

function StatusDot({ dot, text, label }: { dot: string; text: string; label: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] font-semibold ${text}`}>
      <span className={`w-2 h-2 rounded-full ${dot}`} />
      {label}
    </span>
  )
}

function PriorityBadge({ priority }: { priority: string }) {
  if (priority === 'urgent') return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-700 uppercase tracking-wide">Urgent</span>
  )
  if (priority === 'low') return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-400 uppercase tracking-wide">Low</span>
  )
  return null
}

function ActionBtn({ label, variant = 'primary', onClick }: { label: string; variant?: 'primary' | 'secondary' | 'danger' | 'emerald'; onClick?: () => void }) {
  const cls = {
    primary:   'bg-blue-600 hover:bg-blue-700 text-white',
    secondary: 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-200',
    danger:    'bg-red-50 hover:bg-red-100 text-red-700 border border-red-200',
    emerald:   'bg-emerald-600 hover:bg-emerald-700 text-white',
  }[variant]
  return (
    <button onClick={onClick} className={`px-3 py-1.5 rounded-lg text-[13px] font-medium transition-colors ${cls}`}>
      {label}
    </button>
  )
}

function ReadOnlyLabel() {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-100 border border-slate-200 w-fit">
      <IconLock />
      <span className="text-[12px] font-medium text-slate-400">Read Only — Controller View</span>
    </div>
  )
}

// ─── Create modal (Tower Manager only) ────────────────────────────────────────

interface CreateModalProps {
  step: number
  createType: 'delivery' | 'receiving' | null
  createVin: string
  createDealer: string
  createPriority: 'normal' | 'urgent'
  createDue: string
  createNotes: string
  setStep: (n: number) => void
  setCreateType: (t: 'delivery' | 'receiving') => void
  setCreateVin: (v: string) => void
  setCreateDealer: (d: string) => void
  setCreatePriority: (p: 'normal' | 'urgent') => void
  setCreateDue: (d: string) => void
  setCreateNotes: (n: string) => void
  onClose: () => void
  onSubmit: () => void
}

function CreateModal(props: CreateModalProps) {
  const { step, createType, createVin, createDealer, createPriority, createDue, createNotes,
    setStep, setCreateType, setCreateVin, setCreateDealer, setCreatePriority, setCreateDue, setCreateNotes,
    onClose, onSubmit } = props

  const stepLabels = ['Choose Type', 'Vehicle', 'Dealership', 'Details']
  const canContinue = (step === 1 && !!createType) || (step === 2 && !!createVin.trim()) || (step === 3 && !!createDealer) || step === 4

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">New Transportation Request</p>
            <p className="text-[15px] font-bold text-slate-800 mt-0.5">Step {step} of 4 — {stepLabels[step - 1]}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 transition-colors">
            <IconX />
          </button>
        </div>

        {/* Step indicator */}
        <div className="flex px-6 pt-4 gap-1.5">
          {[1,2,3,4].map(s => (
            <div key={s} className={`h-1 flex-1 rounded-full transition-colors ${s <= step ? 'bg-blue-600' : 'bg-slate-100'}`} />
          ))}
        </div>

        {/* Body */}
        <div className="px-6 py-5 min-h-[220px]">
          {step === 1 && (
            <div className="space-y-3">
              <p className="text-[13px] text-slate-500 mb-4">What type of transportation request is this?</p>
              {(['delivery', 'receiving'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setCreateType(t)}
                  className={`w-full text-left px-4 py-3 rounded-xl border-2 transition-all ${createType === t ? 'border-blue-600 bg-blue-50' : 'border-slate-200 hover:border-slate-300'}`}
                >
                  <p className={`text-[13px] font-semibold ${createType === t ? 'text-blue-700' : 'text-slate-700'}`}>
                    {t === 'delivery' ? 'Delivery — We send our vehicle' : 'Receiving — Dealership brings to us'}
                  </p>
                  <p className="text-[12px] text-slate-400 mt-0.5">
                    {t === 'delivery' ? 'Our driver takes a vehicle to another dealership.' : 'Another dealership delivers a vehicle to our lot.'}
                  </p>
                </button>
              ))}
            </div>
          )}

          {step === 2 && (
            <div>
              <p className="text-[13px] text-slate-500 mb-4">Enter the stock number or VIN of the vehicle involved.</p>
              <label className="block text-[12px] font-semibold text-slate-600 mb-1.5">Stock # or VIN</label>
              <input
                value={createVin}
                onChange={e => setCreateVin(e.target.value)}
                placeholder="e.g. H72840 or 1HGBH41JXMN109186"
                className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-[13px] text-slate-800 placeholder-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}

          {step === 3 && (
            <div>
              <p className="text-[13px] text-slate-500 mb-4">Select the dealership for this trade.</p>
              <div className="space-y-2">
                {DEALERS.map(d => (
                  <label key={d} className={`flex items-center gap-3 px-4 py-3 rounded-xl border-2 cursor-pointer transition-all ${createDealer === d ? 'border-blue-600 bg-blue-50' : 'border-slate-200 hover:border-slate-300'}`}>
                    <input
                      type="radio"
                      name="dealer"
                      value={d}
                      checked={createDealer === d}
                      onChange={() => setCreateDealer(d)}
                      className="accent-blue-600"
                    />
                    <span className={`text-[13px] font-medium ${createDealer === d ? 'text-blue-700' : 'text-slate-700'}`}>{d}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <div>
                <label className="block text-[12px] font-semibold text-slate-600 mb-1.5">Due by (optional)</label>
                <input
                  type="time"
                  value={createDue}
                  onChange={e => setCreateDue(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-[13px] text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-[12px] font-semibold text-slate-600 mb-1.5">Priority</label>
                <div className="flex gap-2">
                  {(['normal', 'urgent'] as const).map(p => (
                    <label key={p} className={`flex items-center gap-2 px-4 py-2 rounded-xl border-2 cursor-pointer transition-all flex-1 justify-center ${createPriority === p ? (p === 'urgent' ? 'border-red-500 bg-red-50' : 'border-blue-600 bg-blue-50') : 'border-slate-200 hover:border-slate-300'}`}>
                      <input type="radio" name="priority" value={p} checked={createPriority === p} onChange={() => setCreatePriority(p)} className="sr-only" />
                      <span className={`text-[13px] font-semibold capitalize ${createPriority === p ? (p === 'urgent' ? 'text-red-700' : 'text-blue-700') : 'text-slate-600'}`}>{p}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-[12px] font-semibold text-slate-600 mb-1.5">Internal Notes (optional)</label>
                <textarea
                  value={createNotes}
                  onChange={e => setCreateNotes(e.target.value)}
                  placeholder="Add any notes for the driver or receiving team…"
                  rows={3}
                  className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-[13px] text-slate-800 placeholder-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 bg-slate-50">
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-[13px] font-medium text-slate-500 hover:text-slate-700 transition-colors">
            Cancel
          </button>
          <div className="flex gap-2">
            {step > 1 && (
              <button onClick={() => setStep(step - 1)} className="px-4 py-2 rounded-lg text-[13px] font-medium bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors">
                Back
              </button>
            )}
            {step < 4 ? (
              <button
                onClick={() => setStep(step + 1)}
                disabled={!canContinue}
                className="px-4 py-2 rounded-lg text-[13px] font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Continue
              </button>
            ) : (
              <button
                onClick={onSubmit}
                className="px-4 py-2 rounded-lg text-[13px] font-medium bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
              >
                Create Request
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Dealer Trades Tab ────────────────────────────────────────────────────────

const TRADE_FILTER_LABELS: { key: string; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'awaiting-pickup', label: 'Awaiting Pickup' },
  { key: 'in-transit', label: 'In Transit' },
  { key: 'returned', label: 'Returned' },
  { key: 'completed', label: 'Completed' },
  { key: 'cancelled', label: 'Cancelled' },
]

function TradeDetailPane({ trade, role, statuses, setStatuses }: {
  trade: DealerTrade
  role: AppRole
  statuses: Record<string, string>
  setStatuses: React.Dispatch<React.SetStateAction<Record<string, string>>>
}) {
  const currentStatus = (statuses[trade.id] ?? trade.status) as TradeStatus
  const st = tradeStat[currentStatus]
  const isReadOnly = role === 'Controller'

  const transition = (next: TradeStatus) => setStatuses(p => ({ ...p, [trade.id]: next }))

  return (
    <div className="flex-1 min-w-0 bg-slate-50 flex flex-col overflow-y-auto">
      {/* Trade header */}
      <div className="bg-white border-b border-slate-100 px-6 py-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">Dealer Trade</p>
            <p className="text-[18px] font-bold text-slate-800 mt-0.5">{trade.tradeNumber}</p>
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              <StatusDot {...st} />
              <PriorityBadge priority={trade.priority} />
              <span className="text-[11px] text-slate-400">Updated {trade.updatedLabel}</span>
            </div>
          </div>
          {isReadOnly && <ReadOnlyLabel />}
        </div>
      </div>

      <div className="flex-1 px-6 py-5 space-y-4">
        {/* Route card */}
        <div className="bg-white rounded-xl border border-slate-100 p-4">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-3">Route</p>
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <p className="text-[11px] text-slate-400 mb-0.5">From</p>
              <p className="text-[13px] font-semibold text-slate-700">{trade.origin.name}</p>
              <p className="text-[12px] text-slate-400">{trade.origin.city}, {trade.origin.state}</p>
            </div>
            <div className="flex-shrink-0 text-slate-300"><IconArrowRight /></div>
            <div className="flex-1 text-right">
              <p className="text-[11px] text-slate-400 mb-0.5">To</p>
              <p className="text-[13px] font-semibold text-slate-700">{trade.destination.name}</p>
              <p className="text-[12px] text-slate-400">{trade.destination.city}, {trade.destination.state}</p>
            </div>
          </div>
          {role === 'Lot Staff' && (
            <button className="mt-3 w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 text-[12px] font-medium text-slate-600 transition-colors">
              <IconMapPin />
              Open in Maps (placeholder)
            </button>
          )}
        </div>

        {/* Driver / ETA */}
        <div className="bg-white rounded-xl border border-slate-100 p-4">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-3">Assignment</p>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500">
              <IconUser />
            </div>
            <div className="flex-1">
              <p className="text-[13px] font-semibold text-slate-700">
                {trade.assignedDriver ?? <span className="text-slate-400 font-normal italic">Unassigned</span>}
              </p>
              {trade.etaLabel && <p className="text-[12px] text-slate-400">{trade.etaLabel}</p>}
            </div>
          </div>
          {role === 'Lot Manager' && trade.etaLabel && (
            <div className="mt-3 flex items-center gap-1.5 px-2.5 py-2 rounded-lg bg-amber-50 border border-amber-200">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
              <span className="text-[11px] font-semibold text-amber-700">Monitor ETA — {trade.etaLabel}</span>
            </div>
          )}
        </div>

        {/* Vehicles */}
        <div className="bg-white rounded-xl border border-slate-100 p-4">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-3">
            Vehicles ({trade.vehicles.length})
          </p>
          <div className="space-y-2">
            {trade.vehicles.map(v => (
              <div key={v.stock} className="flex items-center gap-3 py-1.5">
                <div className="w-7 h-7 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-400">
                  <IconCar />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] font-semibold text-slate-700 truncate">{v.year} {v.make} {v.model}</p>
                  <p className="text-[11px] text-slate-400">Stock #{v.stock}</p>
                </div>
                <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${v.direction === 'in' ? 'bg-emerald-50 text-emerald-700' : 'bg-blue-50 text-blue-700'}`}>
                  {v.direction === 'in' ? 'In' : 'Out'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Role-aware actions */}
        {!isReadOnly && (
          <div className="bg-white rounded-xl border border-slate-100 p-4">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-3">Actions</p>
            <div className="flex flex-wrap gap-2">
              {role === 'Lot Staff' && (
                <>
                  {currentStatus === 'awaiting-pickup' && (
                    <>
                      <ActionBtn label="Accept Assignment" variant="primary" />
                      <ActionBtn label="Mark Picked Up" variant="secondary" onClick={() => transition('in-transit')} />
                    </>
                  )}
                  {currentStatus === 'in-transit' && (
                    <ActionBtn label="Mark Completed" variant="emerald" onClick={() => transition('completed')} />
                  )}
                  <ActionBtn label="Report Issue" variant="danger" />
                </>
              )}
              {role === 'Lot Manager' && (
                <ActionBtn label="Reassign Driver" variant="secondary" />
              )}
              {role === 'Tower Manager' && (
                <>
                  {!trade.assignedDriver && <ActionBtn label="Assign Driver" variant="primary" />}
                  {trade.assignedDriver && <ActionBtn label="Reassign Driver" variant="secondary" />}
                  {currentStatus !== 'completed' && currentStatus !== 'cancelled' && (
                    <ActionBtn label="Mark Completed" variant="emerald" onClick={() => transition('completed')} />
                  )}
                  {currentStatus !== 'cancelled' && currentStatus !== 'completed' && (
                    <ActionBtn label="Cancel Trade" variant="danger" onClick={() => transition('cancelled')} />
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function DealerTradesTab({ role, tradeFilter, setTradeFilter, selectedTrade, setSelectedTrade, tradeStatuses, setTradeStatuses }: {
  role: AppRole
  tradeFilter: string
  setTradeFilter: (f: string) => void
  selectedTrade: string | null
  setSelectedTrade: (id: string | null) => void
  tradeStatuses: Record<string, string>
  setTradeStatuses: React.Dispatch<React.SetStateAction<Record<string, string>>>
}) {
  const filteredTrades = useMemo(() => {
    return TRADES.filter(t => {
      const effectiveStatus = tradeStatuses[t.id] ?? t.status
      if (tradeFilter !== 'all' && effectiveStatus !== tradeFilter) return false
      return true
    })
  }, [tradeFilter, tradeStatuses])

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: TRADES.length }
    TRADES.forEach(t => {
      const s = tradeStatuses[t.id] ?? t.status
      c[s] = (c[s] ?? 0) + 1
    })
    return c
  }, [tradeStatuses])

  const selected = filteredTrades.find(t => t.id === selectedTrade) ?? null

  return (
    <div className="flex flex-1 min-h-0 gap-0">
      {/* Sidebar */}
      <div className="w-44 flex-shrink-0 bg-white border-r border-slate-100 py-4 flex flex-col gap-1 px-2 overflow-y-auto">
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-2 mb-1">Filter</p>
        {TRADE_FILTER_LABELS.map(f => (
          <button
            key={f.key}
            onClick={() => setTradeFilter(f.key)}
            className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-[12px] font-medium transition-colors text-left ${tradeFilter === f.key ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-50'}`}
          >
            <span>{f.label}</span>
            {counts[f.key] !== undefined && counts[f.key] > 0 && (
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${tradeFilter === f.key ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500'}`}>
                {counts[f.key]}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Center list */}
      <div className="bg-white border-r border-slate-100 flex flex-col overflow-y-auto" style={{ width: 'clamp(220px, 22vw, 290px)' }}>
        {role === 'Lot Staff' && (
          <div className="px-3 py-2 bg-blue-50 border-b border-blue-100">
            <p className="text-[11px] text-blue-700 font-medium leading-snug">Your assignment: <span className="font-bold">DT-2024-0142</span></p>
          </div>
        )}
        {filteredTrades.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-2 px-4 py-12">
            <div className="text-slate-300"><IconTruck /></div>
            <p className="text-[12px] text-slate-400 text-center">No trades match this filter.</p>
          </div>
        ) : (
          filteredTrades.map(trade => {
            const effectiveStatus = (tradeStatuses[trade.id] ?? trade.status) as TradeStatus
            const st = tradeStat[effectiveStatus]
            const isSelected = trade.id === selectedTrade
            const isMyAssignment = role === 'Lot Staff' && trade.tradeNumber === 'DT-2024-0142'
            return (
              <button
                key={trade.id}
                onClick={() => setSelectedTrade(trade.id)}
                className={`w-full text-left px-3 py-3 border-b border-slate-50 transition-colors ${isSelected ? 'bg-blue-50' : 'hover:bg-slate-50'}`}
              >
                <div className="flex items-start justify-between gap-1 mb-1">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <p className={`text-[12px] font-bold truncate ${isSelected ? 'text-blue-700' : 'text-slate-700'}`}>{trade.tradeNumber}</p>
                    {isMyAssignment && (
                      <span className="flex-shrink-0 text-[9px] font-bold bg-blue-600 text-white px-1 py-0.5 rounded uppercase tracking-wide">Mine</span>
                    )}
                  </div>
                  <PriorityBadge priority={trade.priority} />
                </div>
                <StatusDot {...st} />
                <div className="flex items-center gap-1 mt-1.5 text-slate-400">
                  <p className="text-[11px] truncate">{trade.origin.name}</p>
                  <div className="flex-shrink-0"><IconArrowRight /></div>
                  <p className="text-[11px] truncate">{trade.destination.name}</p>
                </div>
                {trade.assignedDriver ? (
                  <p className="text-[11px] text-slate-500 mt-1 flex items-center gap-1 truncate">
                    <span className="flex-shrink-0"><IconUser /></span>
                    {trade.assignedDriver}
                  </p>
                ) : (
                  <p className="text-[11px] text-amber-600 mt-1 italic">No driver assigned</p>
                )}
                {trade.etaLabel && (
                  <p className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                    <span className="flex-shrink-0"><IconClock /></span>
                    {trade.etaLabel}
                  </p>
                )}
                <p className="text-[10px] text-slate-300 mt-1">{trade.updatedLabel}</p>
              </button>
            )
          })
        )}
      </div>

      {/* Detail pane */}
      {selected ? (
        <TradeDetailPane trade={selected} role={role} statuses={tradeStatuses} setStatuses={setTradeStatuses} />
      ) : (
        <div className="flex-1 bg-slate-50 flex flex-col items-center justify-center gap-3 text-slate-300">
          <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center">
            <IconTruck />
          </div>
          <p className="text-[13px] text-slate-400">Select a trade to view details</p>
        </div>
      )}
    </div>
  )
}

// ─── Customer Deliveries Tab ──────────────────────────────────────────────────

const DELIV_FILTER_LABELS: { key: string; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'scheduled', label: 'Scheduled' },
  { key: 'assigned', label: 'Assigned' },
  { key: 'en-route', label: 'En Route' },
  { key: 'delivered', label: 'Delivered' },
  { key: 'cancelled', label: 'Cancelled' },
]

function DeliveryDetailPane({ delivery, role, statuses, setStatuses }: {
  delivery: CustomerDelivery
  role: AppRole
  statuses: Record<string, string>
  setStatuses: React.Dispatch<React.SetStateAction<Record<string, string>>>
}) {
  const currentStatus = (statuses[delivery.id] ?? delivery.status) as DelivStatus
  const st = delivStat[currentStatus]
  const isReadOnly = role === 'Controller'

  const transition = (next: DelivStatus) => setStatuses(p => ({ ...p, [delivery.id]: next }))

  const timelineSteps: DelivStatus[] = ['scheduled', 'assigned', 'en-route', 'delivered']
  const currentIdx = timelineSteps.indexOf(currentStatus)

  return (
    <div className="flex-1 min-w-0 bg-slate-50 flex flex-col overflow-y-auto">
      {/* Header */}
      <div className="bg-white border-b border-slate-100 px-6 py-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">Customer Delivery</p>
            <p className="text-[18px] font-bold text-slate-800 mt-0.5">{delivery.deliveryNumber}</p>
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              <StatusDot {...st} />
              <PriorityBadge priority={delivery.priority} />
              <span className="text-[11px] text-slate-400">Updated {delivery.updatedLabel}</span>
            </div>
          </div>
          {isReadOnly && <ReadOnlyLabel />}
        </div>
      </div>

      <div className="flex-1 px-6 py-5 space-y-4">
        {/* Customer card */}
        <div className="bg-white rounded-xl border border-slate-100 p-4">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-3">Customer</p>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
              <IconUser />
            </div>
            <div className="flex-1">
              <p className="text-[14px] font-bold text-slate-700">{delivery.customer.name}</p>
              <div className="flex items-center gap-1.5 mt-0.5 text-slate-400">
                <IconPhone />
                <p className="text-[12px]">{delivery.customer.phone}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Vehicle card */}
        <div className="bg-white rounded-xl border border-slate-100 p-4">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-3">Vehicle</p>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-400">
              <IconCar />
            </div>
            <div>
              <p className="text-[13px] font-semibold text-slate-700">{delivery.vehicle.year} {delivery.vehicle.make} {delivery.vehicle.model}</p>
              <p className="text-[12px] text-slate-400">{delivery.vehicle.color} · Stock #{delivery.vehicle.stock}</p>
            </div>
          </div>
        </div>

        {/* Delivery details */}
        <div className="bg-white rounded-xl border border-slate-100 p-4">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-3">Delivery Details</p>
          <div className="space-y-2.5">
            <div className="flex items-start gap-2.5">
              <div className="mt-0.5 text-slate-400 flex-shrink-0"><IconMapPin /></div>
              <div>
                <p className="text-[11px] text-slate-400">Delivery Address</p>
                <p className="text-[13px] font-medium text-slate-700">{delivery.deliveryAddress}</p>
              </div>
            </div>
            <div className="flex items-start gap-2.5">
              <div className="mt-0.5 text-slate-400 flex-shrink-0"><IconClock /></div>
              <div>
                <p className="text-[11px] text-slate-400">Scheduled Time</p>
                <p className="text-[13px] font-medium text-slate-700">{delivery.scheduledTime}</p>
                {delivery.etaLabel && (
                  <p className="text-[12px] text-emerald-600 font-medium mt-0.5">{delivery.etaLabel}</p>
                )}
              </div>
            </div>
            <div className="flex items-start gap-2.5">
              <div className="mt-0.5 text-slate-400 flex-shrink-0"><IconUser /></div>
              <div>
                <p className="text-[11px] text-slate-400">Driver</p>
                <p className={`text-[13px] font-medium ${delivery.assignedDriver ? 'text-slate-700' : 'text-amber-600 italic'}`}>
                  {delivery.assignedDriver ?? 'Unassigned'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Timeline */}
        <div className="bg-white rounded-xl border border-slate-100 p-4">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-3">Timeline</p>
          <div className="flex flex-col gap-2">
            {timelineSteps.map((s, stepIdx) => {
              const done = stepIdx < currentIdx
              const active = stepIdx === currentIdx
              return (
                <div key={s} className="flex items-center gap-3">
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${done ? 'bg-emerald-500' : active ? 'bg-blue-600' : 'bg-slate-100'}`}>
                    {done ? (
                      <IconCheck />
                    ) : (
                      <span className={`w-2 h-2 rounded-full ${active ? 'bg-white' : 'bg-slate-300'}`} />
                    )}
                  </div>
                  <p className={`text-[12px] font-medium ${done ? 'text-emerald-600' : active ? 'text-blue-700' : 'text-slate-400'}`}>
                    {delivStat[s].label}
                  </p>
                  {active && <span className="ml-auto text-[10px] font-semibold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">Current</span>}
                </div>
              )
            })}
          </div>
        </div>

        {/* Actions */}
        {!isReadOnly && (
          <div className="bg-white rounded-xl border border-slate-100 p-4">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-3">Actions</p>
            <div className="flex flex-wrap gap-2">
              {role === 'Lot Staff' && (
                <>
                  {currentStatus === 'scheduled' && <ActionBtn label="Accept" variant="primary" onClick={() => transition('assigned')} />}
                  {currentStatus === 'assigned' && <ActionBtn label="Mark En Route" variant="primary" onClick={() => transition('en-route')} />}
                  {currentStatus === 'en-route' && <ActionBtn label="Mark Delivered" variant="emerald" onClick={() => transition('delivered')} />}
                  <ActionBtn label="Report Issue" variant="danger" />
                </>
              )}
              {role === 'Lot Manager' && (
                <>
                  <ActionBtn label="Reassign Driver" variant="secondary" />
                  {currentStatus === 'en-route' && (
                    <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-amber-50 border border-amber-200">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                      <span className="text-[11px] font-semibold text-amber-700">Monitor delivery</span>
                    </div>
                  )}
                </>
              )}
              {role === 'Tower Manager' && (
                <>
                  {!delivery.assignedDriver && <ActionBtn label="Assign Driver" variant="primary" />}
                  {delivery.assignedDriver && <ActionBtn label="Reassign Driver" variant="secondary" />}
                  {currentStatus !== 'delivered' && currentStatus !== 'cancelled' && (
                    <ActionBtn label="Mark Delivered" variant="emerald" onClick={() => transition('delivered')} />
                  )}
                  {currentStatus !== 'cancelled' && currentStatus !== 'delivered' && (
                    <ActionBtn label="Cancel Delivery" variant="danger" onClick={() => transition('cancelled')} />
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function CustomerDeliveriesTab({ role, delivFilter, setDelivFilter, selectedDelivery, setSelectedDelivery, delivStatuses, setDelivStatuses }: {
  role: AppRole
  delivFilter: string
  setDelivFilter: (f: string) => void
  selectedDelivery: string | null
  setSelectedDelivery: (id: string | null) => void
  delivStatuses: Record<string, string>
  setDelivStatuses: React.Dispatch<React.SetStateAction<Record<string, string>>>
}) {
  const filteredDeliveries = useMemo(() => {
    return DELIVERIES.filter(d => {
      const effectiveStatus = delivStatuses[d.id] ?? d.status
      if (delivFilter !== 'all' && effectiveStatus !== delivFilter) return false
      return true
    })
  }, [delivFilter, delivStatuses])

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: DELIVERIES.length }
    DELIVERIES.forEach(d => {
      const s = delivStatuses[d.id] ?? d.status
      c[s] = (c[s] ?? 0) + 1
    })
    return c
  }, [delivStatuses])

  const selected = filteredDeliveries.find(d => d.id === selectedDelivery) ?? null

  return (
    <div className="flex flex-1 min-h-0 gap-0">
      {/* Sidebar */}
      <div className="w-44 flex-shrink-0 bg-white border-r border-slate-100 py-4 flex flex-col gap-1 px-2 overflow-y-auto">
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-2 mb-1">Filter</p>
        {DELIV_FILTER_LABELS.map(f => (
          <button
            key={f.key}
            onClick={() => setDelivFilter(f.key)}
            className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-[12px] font-medium transition-colors text-left ${delivFilter === f.key ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-50'}`}
          >
            <span>{f.label}</span>
            {counts[f.key] !== undefined && counts[f.key] > 0 && (
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${delivFilter === f.key ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500'}`}>
                {counts[f.key]}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Center list */}
      <div className="bg-white border-r border-slate-100 flex flex-col overflow-y-auto" style={{ width: 'clamp(220px, 22vw, 290px)' }}>
        {filteredDeliveries.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-2 px-4 py-12">
            <div className="text-slate-300"><IconCar /></div>
            <p className="text-[12px] text-slate-400 text-center">No deliveries match this filter.</p>
          </div>
        ) : (
          filteredDeliveries.map(delivery => {
            const effectiveStatus = (delivStatuses[delivery.id] ?? delivery.status) as DelivStatus
            const st = delivStat[effectiveStatus]
            const isSelected = delivery.id === selectedDelivery
            return (
              <button
                key={delivery.id}
                onClick={() => setSelectedDelivery(delivery.id)}
                className={`w-full text-left px-3 py-3 border-b border-slate-50 transition-colors ${isSelected ? 'bg-blue-50' : 'hover:bg-slate-50'}`}
              >
                <div className="flex items-start justify-between gap-1 mb-1">
                  <p className={`text-[12px] font-bold ${isSelected ? 'text-blue-700' : 'text-slate-700'}`}>{delivery.deliveryNumber}</p>
                  <PriorityBadge priority={delivery.priority} />
                </div>
                <StatusDot {...st} />
                <p className="text-[12px] font-semibold text-slate-600 mt-1.5 truncate">{delivery.customer.name}</p>
                <p className="text-[11px] text-slate-400 truncate">{delivery.vehicle.year} {delivery.vehicle.make} {delivery.vehicle.model}</p>
                <div className="flex items-center gap-1 mt-1 text-slate-400">
                  <span className="flex-shrink-0"><IconClock /></span>
                  <p className="text-[11px] truncate">{delivery.scheduledTime}</p>
                </div>
                {delivery.assignedDriver ? (
                  <p className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-1 truncate">
                    <span className="flex-shrink-0"><IconUser /></span>
                    {delivery.assignedDriver}
                  </p>
                ) : (
                  <p className="text-[11px] text-amber-600 mt-0.5 italic">No driver assigned</p>
                )}
                <p className="text-[10px] text-slate-300 mt-1">{delivery.updatedLabel}</p>
              </button>
            )
          })
        )}
      </div>

      {/* Detail pane */}
      {selected ? (
        <DeliveryDetailPane delivery={selected} role={role} statuses={delivStatuses} setStatuses={setDelivStatuses} />
      ) : (
        <div className="flex-1 bg-slate-50 flex flex-col items-center justify-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-300">
            <IconCar />
          </div>
          <p className="text-[13px] text-slate-400">Select a delivery to view details</p>
        </div>
      )}
    </div>
  )
}

// ─── Role badge colors ────────────────────────────────────────────────────────

const roleBadgeClass: Record<AppRole, string> = {
  'Lot Staff':      'bg-slate-100 text-slate-600',
  'Lot Manager':    'bg-blue-100 text-blue-700',
  'Tower Manager':  'bg-violet-100 text-violet-700',
  'Controller':     'bg-emerald-100 text-emerald-700',
  'Sales Manager':  'bg-amber-100 text-amber-700',
  'Recon Manager':  'bg-orange-100 text-orange-700',
  'Service Advisor':'bg-cyan-100 text-cyan-700',
  'Detail Team':    'bg-pink-100 text-pink-700',
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function Transportation({ role }: { role: AppRole }): JSX.Element {
  const [activeTab, setActiveTab] = useState<'trades' | 'deliveries'>('trades')
  const [selectedTrade, setSelectedTrade] = useState<string | null>(null)
  const [selectedDelivery, setSelectedDelivery] = useState<string | null>(null)
  const [tradeFilter, setTradeFilter] = useState<string>('all')
  const [delivFilter, setDelivFilter] = useState<string>('all')
  const [tradeStatuses, setTradeStatuses] = useState<Record<string, string>>({})
  const [delivStatuses, setDelivStatuses] = useState<Record<string, string>>({})
  const [showCreate, setShowCreate] = useState(false)
  const [createStep, setCreateStep] = useState(1)
  const [createType, setCreateType] = useState<'delivery' | 'receiving' | null>(null)
  const [createVin, setCreateVin] = useState('')
  const [createDealer, setCreateDealer] = useState('')
  const [createPriority, setCreatePriority] = useState<'normal' | 'urgent'>('normal')
  const [createDue, setCreateDue] = useState('')
  const [createNotes, setCreateNotes] = useState('')

  const handleOpenCreate = () => {
    setCreateStep(1)
    setCreateType(null)
    setCreateVin('')
    setCreateDealer('')
    setCreatePriority('normal')
    setCreateDue('')
    setCreateNotes('')
    setShowCreate(true)
  }

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-100 px-6 py-3 flex items-center gap-4 flex-shrink-0 flex-wrap">
        <div className="flex items-center gap-2.5 mr-2">
          <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center text-white">
            <IconTruck />
          </div>
          <h1 className="text-[17px] font-bold text-slate-800">Transportation</h1>
        </div>

        {/* Tab switcher */}
        <div className="flex items-center bg-slate-100 rounded-lg p-0.5 gap-0.5">
          <button
            onClick={() => setActiveTab('trades')}
            className={`px-3 py-1.5 rounded-md text-[12px] font-semibold transition-all ${activeTab === 'trades' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            Dealer Trades
          </button>
          <button
            onClick={() => setActiveTab('deliveries')}
            className={`px-3 py-1.5 rounded-md text-[12px] font-semibold transition-all ${activeTab === 'deliveries' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            Customer Deliveries
          </button>
        </div>

        <div className="flex-1" />

        {/* Role badge */}
        <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full ${roleBadgeClass[role]}`}>
          {role}
        </span>

        {/* Tower Manager new request button */}
        {role === 'Tower Manager' && (
          <button
            onClick={handleOpenCreate}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-[12px] font-semibold transition-colors"
          >
            <IconPlus />
            New Request
          </button>
        )}
      </div>

      {/* Tab content */}
      <div className="flex flex-1 min-h-0">
        {activeTab === 'trades' ? (
          <DealerTradesTab
            role={role}
            tradeFilter={tradeFilter}
            setTradeFilter={setTradeFilter}
            selectedTrade={selectedTrade}
            setSelectedTrade={setSelectedTrade}
            tradeStatuses={tradeStatuses}
            setTradeStatuses={setTradeStatuses}
          />
        ) : (
          <CustomerDeliveriesTab
            role={role}
            delivFilter={delivFilter}
            setDelivFilter={setDelivFilter}
            selectedDelivery={selectedDelivery}
            setSelectedDelivery={setSelectedDelivery}
            delivStatuses={delivStatuses}
            setDelivStatuses={setDelivStatuses}
          />
        )}
      </div>

      {/* Create modal — Tower Manager only */}
      {showCreate && (
        <CreateModal
          step={createStep}
          createType={createType}
          createVin={createVin}
          createDealer={createDealer}
          createPriority={createPriority}
          createDue={createDue}
          createNotes={createNotes}
          setStep={setCreateStep}
          setCreateType={setCreateType}
          setCreateVin={setCreateVin}
          setCreateDealer={setCreateDealer}
          setCreatePriority={setCreatePriority}
          setCreateDue={setCreateDue}
          setCreateNotes={setCreateNotes}
          onClose={() => setShowCreate(false)}
          onSubmit={() => setShowCreate(false)}
        />
      )}
    </div>
  )
}
