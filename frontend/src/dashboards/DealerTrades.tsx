// DealerTrades.tsx — Tower Manager: Dealer Trade workspace

import { useState, useMemo } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

type TradeStatus   = 'awaiting-pickup' | 'in-transit' | 'returned' | 'completed' | 'cancelled'
type TradePriority = 'urgent' | 'normal' | 'low'

interface TradeVehicle {
  stock: string; vin: string; year: number; make: string; model: string
  color: string; direction: 'incoming' | 'outgoing'
}

interface TimelineEvent {
  label: string; sublabel?: string; done: boolean; active?: boolean
}

interface DealerTrade {
  id: string; tradeNumber: string
  status: TradeStatus; priority: TradePriority
  origin: { name: string; city: string; state: string; contact?: string }
  destination: { name: string; city: string; state: string; contact?: string }
  pickupLocation: string; returnLocation: string
  assignedDriver?: string
  etaLabel?: string; etaMinutes?: number
  vehicles: TradeVehicle[]
  paperwork: { label: string; done: boolean }[]
  timeline: TimelineEvent[]
  notes?: string
  createdBy: string; createdLabel: string; updatedLabel: string
}

// ─── Data ─────────────────────────────────────────────────────────────────────

const TRADES: DealerTrade[] = [
  {
    id: 't1', tradeNumber: 'DT-2024-0142', status: 'awaiting-pickup', priority: 'urgent',
    origin: { name: 'Crown Honda', city: 'Riverside', state: 'CA', contact: 'Mike T. · (951) 555-0182' },
    destination: { name: 'LotSync Auto Group', city: 'Anaheim', state: 'CA' },
    pickupLocation: 'Crown Honda — 1420 Auto Center Dr, Riverside, CA 92507',
    returnLocation: 'LotSync Auto Group — Main Lot Receiving',
    assignedDriver: undefined,
    etaLabel: 'ASAP', etaMinutes: -1,
    vehicles: [
      { stock: 'H72840', vin: '1HGBH41JXMN109186', year: 2023, make: 'Subaru', model: 'Outback', color: 'Crystal White', direction: 'incoming' },
      { stock: 'G19283', vin: '2T1BURHE0JC040323', year: 2022, make: 'Toyota', model: 'RAV4', color: 'Magnetic Gray', direction: 'incoming' },
      { stock: 'B39281', vin: '1HGCV1F13LA012233', year: 2024, make: 'Honda', model: 'CR-V', color: 'Sonic Gray Pearl', direction: 'incoming' },
    ],
    paperwork: [
      { label: 'Trade Agreement (signed)', done: true },
      { label: 'Title Transfer Form', done: true },
      { label: 'Dealer License Copy', done: false },
      { label: 'Odometer Disclosure', done: false },
      { label: 'Dealer Plates', done: false },
    ],
    timeline: [
      { label: 'Trade Created', sublabel: 'Rosa Pereira · 8:42 AM', done: true },
      { label: 'Paperwork Submitted', sublabel: 'Partial — 2 of 5', done: true },
      { label: 'Driver Assigned', sublabel: 'Pending', done: false, active: true },
      { label: 'Vehicle Pickup', sublabel: 'Pending', done: false },
      { label: 'In Transit', sublabel: '', done: false },
      { label: 'Received', sublabel: '', done: false },
    ],
    notes: 'Mike at Crown Honda is expecting us. Call ahead before arriving — they need 30 min notice to pull vehicles. Dealer plates are in the key cabinet.',
    createdBy: 'Rosa Pereira', createdLabel: 'Today · 8:42 AM', updatedLabel: '2 min ago',
  },
  {
    id: 't2', tradeNumber: 'DT-2024-0141', status: 'in-transit', priority: 'normal',
    origin: { name: 'Sunrise Toyota', city: 'Fullerton', state: 'CA', contact: 'Janet L. · (714) 555-0243' },
    destination: { name: 'LotSync Auto Group', city: 'Anaheim', state: 'CA' },
    pickupLocation: 'Sunrise Toyota — 2800 Harbor Blvd, Fullerton, CA 92835',
    returnLocation: 'LotSync Auto Group — Main Lot Receiving',
    assignedDriver: 'Marcus Torres',
    etaLabel: 'Today 2:30 PM', etaMinutes: 150,
    vehicles: [
      { stock: 'K29011', vin: '4T1BF1FK5HU791223', year: 2024, make: 'Toyota', model: 'Camry', color: 'Midnight Black', direction: 'incoming' },
      { stock: 'K29012', vin: '2T3P1RFV8LW085941', year: 2024, make: 'Toyota', model: 'RAV4 Hybrid', color: 'Blueprint', direction: 'incoming' },
    ],
    paperwork: [
      { label: 'Trade Agreement (signed)', done: true },
      { label: 'Title Transfer Form', done: true },
      { label: 'Dealer License Copy', done: true },
      { label: 'Odometer Disclosure', done: true },
      { label: 'Dealer Plates', done: true },
    ],
    timeline: [
      { label: 'Trade Created', sublabel: 'Rosa Pereira · Yesterday 4:10 PM', done: true },
      { label: 'Paperwork Submitted', sublabel: 'Complete', done: true },
      { label: 'Driver Assigned', sublabel: 'Marcus Torres', done: true },
      { label: 'Vehicle Pickup', sublabel: 'Today 10:47 AM', done: true },
      { label: 'In Transit', sublabel: 'ETA 2:30 PM', done: false, active: true },
      { label: 'Received', sublabel: '', done: false },
    ],
    createdBy: 'Rosa Pereira', createdLabel: 'Yesterday · 4:10 PM', updatedLabel: '14 min ago',
  },
  {
    id: 't3', tradeNumber: 'DT-2024-0140', status: 'in-transit', priority: 'normal',
    origin: { name: 'LotSync Auto Group', city: 'Anaheim', state: 'CA' },
    destination: { name: 'Westside Kia', city: 'Santa Monica', state: 'CA', contact: 'Dave R. · (310) 555-0319' },
    pickupLocation: 'LotSync Auto Group — Front Lot',
    returnLocation: 'Westside Kia — 2100 Santa Monica Blvd',
    assignedDriver: 'K. Williams',
    etaLabel: 'Today 4:00 PM', etaMinutes: 270,
    vehicles: [
      { stock: 'D72044', vin: '5XYPH4A18MG191023', year: 2024, make: 'Kia', model: 'Telluride', color: 'Everest White', direction: 'outgoing' },
    ],
    paperwork: [
      { label: 'Trade Agreement (signed)', done: true },
      { label: 'Title Transfer Form', done: true },
      { label: 'Dealer License Copy', done: true },
      { label: 'Odometer Disclosure', done: true },
      { label: 'Dealer Plates', done: true },
    ],
    timeline: [
      { label: 'Trade Created', sublabel: 'Rosa Pereira · Yesterday 2:30 PM', done: true },
      { label: 'Paperwork Submitted', sublabel: 'Complete', done: true },
      { label: 'Driver Assigned', sublabel: 'K. Williams', done: true },
      { label: 'Vehicle Pickup', sublabel: 'Today 11:20 AM', done: true },
      { label: 'In Transit', sublabel: 'ETA 4:00 PM', done: false, active: true },
      { label: 'Delivered', sublabel: '', done: false },
    ],
    createdBy: 'Rosa Pereira', createdLabel: 'Yesterday · 2:30 PM', updatedLabel: '1h ago',
  },
  {
    id: 't4', tradeNumber: 'DT-2024-0139', status: 'awaiting-pickup', priority: 'normal',
    origin: { name: 'AutoNation BMW', city: 'Buena Park', state: 'CA', contact: 'Chris M. · (714) 555-0481' },
    destination: { name: 'LotSync Auto Group', city: 'Anaheim', state: 'CA' },
    pickupLocation: 'AutoNation BMW — 5700 Auto Center Dr, Buena Park, CA 90621',
    returnLocation: 'LotSync Auto Group — Premium Receiving Bay',
    assignedDriver: 'Jordan Davis',
    etaLabel: 'Today 3:00 PM', etaMinutes: 210,
    vehicles: [
      { stock: 'E51388', vin: 'WBA3N9C51FK223118', year: 2023, make: 'BMW', model: '5 Series', color: 'Mineral White', direction: 'incoming' },
      { stock: 'E51389', vin: 'WBA5N7C51JGY32942', year: 2023, make: 'BMW', model: '3 Series', color: 'Black Sapphire', direction: 'incoming' },
      { stock: 'E51390', vin: '5UXKR0C50H0V76231', year: 2022, make: 'BMW', model: 'X5', color: 'Alpine White', direction: 'incoming' },
      { stock: 'E51391', vin: 'WBS3R9C55FK387129', year: 2023, make: 'BMW', model: 'M3', color: 'Frozen Red', direction: 'incoming' },
    ],
    paperwork: [
      { label: 'Trade Agreement (signed)', done: true },
      { label: 'Title Transfer Form', done: true },
      { label: 'Dealer License Copy', done: true },
      { label: 'Odometer Disclosure', done: false },
      { label: 'Dealer Plates', done: true },
    ],
    timeline: [
      { label: 'Trade Created', sublabel: 'Rosa Pereira · Today 7:15 AM', done: true },
      { label: 'Paperwork Submitted', sublabel: 'Partial — 4 of 5', done: true },
      { label: 'Driver Assigned', sublabel: 'Jordan Davis', done: true },
      { label: 'Vehicle Pickup', sublabel: 'Scheduled 1:30 PM', done: false, active: true },
      { label: 'In Transit', sublabel: '', done: false },
      { label: 'Received', sublabel: '', done: false },
    ],
    createdBy: 'Rosa Pereira', createdLabel: 'Today · 7:15 AM', updatedLabel: '3h ago',
  },
  {
    id: 't5', tradeNumber: 'DT-2024-0138', status: 'returned', priority: 'normal',
    origin: { name: 'LotSync Auto Group', city: 'Anaheim', state: 'CA' },
    destination: { name: 'Riverside Ford', city: 'Riverside', state: 'CA' },
    pickupLocation: 'LotSync Auto Group — Front Lot',
    returnLocation: 'Riverside Ford — Receiving Dock',
    assignedDriver: 'Marcus Torres',
    etaLabel: 'Returned 1h ago',
    vehicles: [
      { stock: 'F29917', vin: '1FTEW1E82MKD74819', year: 2022, make: 'Chevrolet', model: 'Silverado', color: 'Black', direction: 'outgoing' },
      { stock: 'F29918', vin: '1FTFW1E80MFA11982', year: 2022, make: 'Ford', model: 'F-150', color: 'Oxford White', direction: 'outgoing' },
    ],
    paperwork: [
      { label: 'Trade Agreement (signed)', done: true },
      { label: 'Title Transfer Form', done: true },
      { label: 'Dealer License Copy', done: true },
      { label: 'Odometer Disclosure', done: true },
      { label: 'Dealer Plates', done: true },
    ],
    timeline: [
      { label: 'Trade Created', sublabel: 'Yesterday 9:00 AM', done: true },
      { label: 'Paperwork Submitted', sublabel: 'Complete', done: true },
      { label: 'Driver Assigned', sublabel: 'Marcus Torres', done: true },
      { label: 'Vehicle Pickup', sublabel: 'Yesterday 1:15 PM', done: true },
      { label: 'In Transit', sublabel: 'Yesterday 1:15 PM', done: true },
      { label: 'Delivered', sublabel: 'Today 9:42 AM', done: true },
    ],
    createdBy: 'Rosa Pereira', createdLabel: 'Yesterday · 9:00 AM', updatedLabel: '1h ago',
  },
  {
    id: 't6', tradeNumber: 'DT-2024-0137', status: 'completed', priority: 'normal',
    origin: { name: 'Pacific Honda', city: 'Torrance', state: 'CA' },
    destination: { name: 'LotSync Auto Group', city: 'Anaheim', state: 'CA' },
    pickupLocation: 'Pacific Honda — 2500 Pacific Coast Hwy, Torrance, CA',
    returnLocation: 'LotSync Auto Group — Main Receiving',
    assignedDriver: 'K. Williams',
    vehicles: [
      { stock: 'P28100', vin: '1HGCV1F13LA019921', year: 2023, make: 'Honda', model: 'Accord', color: 'Lunar Silver', direction: 'incoming' },
    ],
    paperwork: [
      { label: 'Trade Agreement (signed)', done: true },
      { label: 'Title Transfer Form', done: true },
      { label: 'Dealer License Copy', done: true },
      { label: 'Odometer Disclosure', done: true },
      { label: 'Dealer Plates', done: true },
    ],
    timeline: [
      { label: 'Trade Created', sublabel: '2 days ago', done: true },
      { label: 'Paperwork Submitted', sublabel: 'Complete', done: true },
      { label: 'Driver Assigned', sublabel: 'K. Williams', done: true },
      { label: 'Vehicle Pickup', sublabel: 'Yesterday 11:00 AM', done: true },
      { label: 'In Transit', sublabel: 'Yesterday 11:00 AM', done: true },
      { label: 'Received & Verified', sublabel: 'Yesterday 2:20 PM', done: true },
    ],
    createdBy: 'Rosa Pereira', createdLabel: '2 days ago', updatedLabel: 'Yesterday',
  },
]

// ─── Config ───────────────────────────────────────────────────────────────────

const statusCfg: Record<TradeStatus, { label: string; dot: string; text: string; bg: string }> = {
  'awaiting-pickup': { label: 'Awaiting Pickup', dot: 'bg-amber-400',   text: 'text-amber-700',   bg: 'bg-amber-50'   },
  'in-transit':      { label: 'In Transit',      dot: 'bg-blue-500',    text: 'text-blue-700',    bg: 'bg-blue-50'    },
  'returned':        { label: 'Returned',         dot: 'bg-emerald-400', text: 'text-emerald-700', bg: 'bg-emerald-50' },
  'completed':       { label: 'Completed',        dot: 'bg-slate-400',   text: 'text-slate-500',   bg: 'bg-slate-50'   },
  'cancelled':       { label: 'Cancelled',        dot: 'bg-slate-300',   text: 'text-slate-400',   bg: 'bg-slate-50'   },
}

const priorityCfg: Record<TradePriority, { label: string; cls: string }> = {
  urgent: { label: 'Urgent', cls: 'bg-red-100 text-red-700 border border-red-200'       },
  normal: { label: 'Normal', cls: 'bg-slate-100 text-slate-500 border border-slate-200' },
  low:    { label: 'Low',    cls: 'bg-slate-50 text-slate-400 border border-slate-200'  },
}

const VIEW_FILTERS: { id: TradeStatus | 'all'; label: string }[] = [
  { id: 'all',             label: 'All Trades'      },
  { id: 'awaiting-pickup', label: 'Awaiting Pickup' },
  { id: 'in-transit',      label: 'In Transit'      },
  { id: 'returned',        label: 'Returned'        },
  { id: 'completed',       label: 'Completed'       },
  { id: 'cancelled',       label: 'Cancelled'       },
]

// ─── Sub-components ───────────────────────────────────────────────────────────

function DirectionArrow() {
  return (
    <svg width="14" height="14" fill="none" viewBox="0 0 24 24" className="text-slate-400 flex-shrink-0">
      <path d="M5 12H19M13 6l6 6-6 6" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function EtaTag({ min, label }: { min?: number; label?: string }) {
  if (!label) return null
  const cls =
    min === -1 ? 'text-red-600 font-bold' :
    min !== undefined && min <= 60 ? 'text-orange-600 font-bold' :
    min !== undefined && min <= 180 ? 'text-amber-600 font-semibold' :
    'text-slate-500'
  return <span className={`text-[10px] ${cls}`}>{label}</span>
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function Sidebar({ view, onView }: { view: TradeStatus | 'all'; onView: (v: TradeStatus | 'all') => void }) {
  const count = (v: TradeStatus | 'all') =>
    v === 'all' ? TRADES.length : TRADES.filter(t => t.status === v).length

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
              {c > 0 && <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${on ? 'bg-white/20' : 'bg-slate-100 text-slate-500'}`}>{c}</span>}
            </button>
          )
        })}
      </div>
    </aside>
  )
}

// ─── Trade list row ───────────────────────────────────────────────────────────

function TradeRow({ t, selected, onSelect }: { t: DealerTrade; selected: boolean; onSelect: () => void }) {
  const sc = statusCfg[t.status]; const pc = priorityCfg[t.priority]
  return (
    <button onClick={onSelect}
      className={`w-full text-left px-3 py-2.5 border-b border-slate-100 transition-all ${
        t.priority === 'urgent' ? 'border-l-2 border-l-red-400' : ''
      } ${selected ? 'bg-blue-50' : 'hover:bg-slate-50'}`}>
      {/* Row 1: trade # + priority + eta */}
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`text-[12.5px] font-bold truncate ${selected ? 'text-blue-700' : 'text-slate-900'}`}>{t.tradeNumber}</span>
          {t.priority === 'urgent' && <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${pc.cls}`}>URGENT</span>}
        </div>
        <EtaTag min={t.etaMinutes} label={t.etaLabel} />
      </div>
      {/* Row 2: route */}
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-[11px] text-slate-600 truncate">{t.origin.name}</span>
        <DirectionArrow />
        <span className="text-[11px] text-slate-600 truncate">{t.destination.name}</span>
      </div>
      {/* Row 3: driver + vehicle count + status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-400">{t.assignedDriver ?? <span className="text-amber-600 font-semibold">Unassigned</span>}</span>
          <span className="text-[9px] font-bold bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded-full">{t.vehicles.length} vehicle{t.vehicles.length !== 1 ? 's' : ''}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className={`w-1.5 h-1.5 rounded-full ${sc.dot}`} />
          <span className={`text-[10px] font-semibold ${sc.text}`}>{sc.label}</span>
        </div>
      </div>
    </button>
  )
}

// ─── Trade detail ─────────────────────────────────────────────────────────────

function TradeDetail({ t, onStatusChange }: { t: DealerTrade; onStatusChange: (id: string, s: TradeStatus) => void }) {
  const [vehicleExpanded, setVehicleExpanded] = useState(false)
  const [paperwork, setPaperwork] = useState(t.paperwork)
  const sc = statusCfg[t.status]; const pc = priorityCfg[t.priority]

  function ActionBar() {
    if (t.status === 'awaiting-pickup') return (
      <div className="flex items-center gap-2">
        {!t.assignedDriver && <button className="text-[12px] font-bold px-4 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Assign Driver</button>}
        {t.assignedDriver && <button onClick={() => onStatusChange(t.id, 'in-transit')} className="text-[12px] font-bold px-4 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Mark Picked Up</button>}
        {t.assignedDriver && <button className="text-[12px] font-semibold px-4 py-1.5 bg-white text-slate-700 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors">Reassign Driver</button>}
        <button onClick={() => onStatusChange(t.id, 'cancelled')} className="text-[12px] text-slate-400 hover:text-red-600 transition-colors px-2">Cancel</button>
      </div>
    )
    if (t.status === 'in-transit') return (
      <div className="flex items-center gap-2">
        <button onClick={() => onStatusChange(t.id, 'returned')} className="text-[12px] font-bold px-4 py-1.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors">Mark Returned</button>
        <button className="text-[12px] font-semibold px-4 py-1.5 bg-white text-slate-700 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors">Reassign Driver</button>
      </div>
    )
    if (t.status === 'returned') return (
      <div className="flex items-center gap-2">
        <button onClick={() => onStatusChange(t.id, 'completed')} className="text-[12px] font-bold px-4 py-1.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors">Complete Trade</button>
      </div>
    )
    if (t.status === 'completed') return <span className="text-[12px] text-emerald-600 font-semibold flex items-center gap-1.5"><svg width="13" height="13" fill="none" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/></svg>Trade Complete</span>
    return null
  }

  const shownVehicles = vehicleExpanded ? t.vehicles : t.vehicles.slice(0, 3)
  const hiddenCount = t.vehicles.length - 3

  return (
    <div className="flex-1 flex flex-col overflow-hidden min-h-0 bg-slate-50">
      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b border-slate-200 px-6 pt-4 pb-3">
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <h2 className="text-[17px] font-bold text-slate-900">{t.tradeNumber}</h2>
              {t.priority === 'urgent' && <span className={`text-[9px] font-bold px-2 py-0.5 rounded ${pc.cls}`}>URGENT</span>}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`w-1.5 h-1.5 rounded-full ${sc.dot}`} />
              <span className={`text-[11px] font-semibold ${sc.text}`}>{sc.label}</span>
              {t.etaLabel && <span className="text-[10px] text-slate-400">· ETA: <span className="font-semibold text-slate-600">{t.etaLabel}</span></span>}
              <span className="text-[10px] text-slate-400">{t.createdLabel}</span>
            </div>
          </div>
        </div>
        <ActionBar />
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3" style={{ scrollbarWidth: 'thin' }}>

        {/* Route card */}
        <div className="bg-white border border-slate-100 rounded-2xl overflow-hidden">
          <div className="grid grid-cols-2 divide-x divide-slate-100">
            <div className="px-5 py-4">
              <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Origin</div>
              <div className="text-[14px] font-bold text-slate-900">{t.origin.name}</div>
              <div className="text-[11px] text-slate-500">{t.origin.city}, {t.origin.state}</div>
              {t.origin.contact && <div className="text-[10px] text-slate-400 mt-1">{t.origin.contact}</div>}
              <div className="text-[10px] text-slate-500 mt-2 leading-snug">{t.pickupLocation.split('—')[1]?.trim() ?? t.pickupLocation}</div>
            </div>
            <div className="px-5 py-4">
              <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Destination</div>
              <div className="text-[14px] font-bold text-slate-900">{t.destination.name}</div>
              <div className="text-[11px] text-slate-500">{t.destination.city}, {t.destination.state}</div>
              {t.destination.contact && <div className="text-[10px] text-slate-400 mt-1">{t.destination.contact}</div>}
              <div className="text-[10px] text-slate-500 mt-2 leading-snug">{t.returnLocation.split('—')[1]?.trim() ?? t.returnLocation}</div>
            </div>
          </div>
          {/* Driver row */}
          <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between">
            <div>
              <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Assigned Driver</div>
              <div className={`text-[13px] font-semibold ${t.assignedDriver ? 'text-slate-900' : 'text-amber-600'}`}>
                {t.assignedDriver ?? 'Unassigned'}
              </div>
            </div>
            {!t.assignedDriver && <button className="text-[11px] font-bold px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Assign</button>}
          </div>
        </div>

        {/* Timeline */}
        <div className="bg-white border border-slate-100 rounded-2xl px-5 pt-4 pb-4">
          <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-3">Timeline</div>
          <div className="space-y-0">
            {t.timeline.map((ev, i) => (
              <div key={i} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${ev.done ? 'bg-emerald-400' : ev.active ? 'bg-blue-500 ring-2 ring-blue-100' : 'bg-slate-200'}`}>
                    {ev.done && <svg width="8" height="8" fill="none" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" stroke="white" strokeWidth="3.5" strokeLinecap="round"/></svg>}
                  </div>
                  {i < t.timeline.length - 1 && <div className={`w-px flex-1 mt-1 mb-1 ${ev.done ? 'bg-emerald-200' : 'bg-slate-100'}`} style={{ minHeight: '16px' }} />}
                </div>
                <div className="pb-3">
                  <div className={`text-[12px] font-semibold ${ev.done ? 'text-slate-700' : ev.active ? 'text-blue-700' : 'text-slate-400'}`}>{ev.label}</div>
                  {ev.sublabel && <div className="text-[10px] text-slate-400">{ev.sublabel}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Vehicles */}
        <div className="bg-white border border-slate-100 rounded-2xl overflow-hidden">
          <div className="px-5 pt-4 pb-3">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Vehicles ({t.vehicles.length})</div>
              {hiddenCount > 0 && <button onClick={() => setVehicleExpanded(e => !e)} className="text-[10px] font-bold text-blue-500 hover:text-blue-700">{vehicleExpanded ? 'Collapse ▲' : `Show ${hiddenCount} more ▼`}</button>}
            </div>
            <div className="space-y-2">
              {shownVehicles.map(v => (
                <div key={v.stock} className="flex items-center gap-3 bg-slate-50 rounded-xl px-3.5 py-2.5">
                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${v.direction === 'incoming' ? 'bg-blue-100 text-blue-600' : 'bg-orange-100 text-orange-600'}`}>
                    {v.direction === 'incoming' ? '↓ IN' : '↑ OUT'}
                  </span>
                  <span className="font-mono text-[11px] font-bold text-blue-600 flex-shrink-0">#{v.stock}</span>
                  <span className="text-[12px] text-slate-700 flex-1 truncate">{v.year} {v.make} {v.model}</span>
                  <span className="text-[10px] text-slate-400">{v.color}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Paperwork */}
        <div className="bg-white border border-slate-100 rounded-2xl px-5 pt-4 pb-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Required Paperwork</div>
            <span className={`text-[10px] font-bold ${paperwork.every(p => p.done) ? 'text-emerald-600' : 'text-amber-600'}`}>
              {paperwork.filter(p => p.done).length} / {paperwork.length}
            </span>
          </div>
          <div className="space-y-1.5">
            {paperwork.map((p, i) => (
              <button key={i} onClick={() => setPaperwork(prev => prev.map((pp, ii) => ii === i ? { ...pp, done: !pp.done } : pp))}
                className="w-full flex items-center gap-2.5 text-left hover:bg-slate-50 rounded-lg px-1 py-1 transition-colors">
                <span className={`w-4 h-4 rounded flex items-center justify-center flex-shrink-0 border ${p.done ? 'bg-emerald-500 border-emerald-500' : 'border-slate-300'}`}>
                  {p.done && <svg width="9" height="9" fill="none" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" stroke="white" strokeWidth="3.5" strokeLinecap="round"/></svg>}
                </span>
                <span className={`text-[12px] ${p.done ? 'text-slate-400 line-through' : 'text-slate-700'}`}>{p.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Notes */}
        {t.notes && (
          <div className="bg-white border border-slate-100 rounded-2xl px-5 pt-4 pb-4">
            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-2">Notes</div>
            <p className="text-[13px] text-slate-700 leading-relaxed">{t.notes}</p>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center gap-x-3 gap-y-1 text-[10px] text-slate-400 px-1 py-2 border-t border-slate-100 flex-wrap">
          <span>Created by <span className="text-slate-500 font-medium">{t.createdBy}</span></span>
          <span className="text-slate-200">·</span>
          <span>{t.createdLabel}</span>
          <span className="text-slate-200">·</span>
          <span>Updated {t.updatedLabel}</span>
        </div>

      </div>
    </div>
  )
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function DealerTrades() {
  const [view,       setView]       = useState<TradeStatus | 'all'>('all')
  const [search,     setSearch]     = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(TRADES[0]?.id ?? null)
  const [statuses,   setStatuses]   = useState<Record<string, TradeStatus>>({})

  const getStatus = (t: DealerTrade): TradeStatus => statuses[t.id] ?? t.status

  const visible = useMemo(() => {
    const q = search.toLowerCase()
    return TRADES
      .map(t => ({ ...t, status: getStatus(t) }))
      .filter(t => view === 'all' || t.status === view)
      .filter(t => !q || [t.tradeNumber, t.origin.name, t.destination.name, t.assignedDriver ?? ''].some(s => s.toLowerCase().includes(q)))
  }, [view, search, statuses])

  const selectedTrade =
    visible.find(t => t.id === selectedId) ??
    TRADES.map(t => ({ ...t, status: getStatus(t) })).find(t => t.id === selectedId)

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
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search trades…"
              className="w-full h-7 pl-7 pr-2 text-[12px] bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 outline-none focus:border-blue-400 transition-colors" />
          </div>
        </div>
        <div className="flex items-center justify-between px-3 py-1.5 border-b border-slate-100">
          <span className="text-[11px] font-bold text-slate-700">Dealer Trades</span>
          <span className="text-[10px] text-slate-400">{visible.length}</span>
        </div>
        <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
          {visible.length === 0 ? (
            <div className="flex items-center justify-center h-24 text-[12px] text-slate-400">No trades found</div>
          ) : (
            visible.map(t => <TradeRow key={t.id} t={t} selected={selectedId === t.id} onSelect={() => setSelectedId(t.id)} />)
          )}
        </div>
      </div>

      {/* Detail */}
      {selectedTrade ? (
        <TradeDetail key={selectedTrade.id} t={selectedTrade} onStatusChange={(id, s) => setStatuses(p => ({ ...p, [id]: s }))} />
      ) : (
        <div className="flex-1 flex items-center justify-center bg-slate-50 text-slate-400">
          <p className="text-[13px]">Select a trade</p>
        </div>
      )}
    </div>
  )
}
