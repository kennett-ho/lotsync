// Requests.tsx — Dispatcher inbox for lot operations

import { useState, useEffect } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

type RequestType   = 'dealer-trade' | 'move-vehicle' | 'delivery' | 'showroom' | 'fuel' | 'detail' | 'service-pull' | 'locate' | 'custom'
type RequestStatus = 'new' | 'accepted' | 'assigned' | 'completed' | 'cancelled'
type Department    = 'tower' | 'sales' | 'service' | 'recon' | 'controller' | 'lot'
type AppRole       = 'Lot Staff' | 'Lot Manager' | 'Tower Manager' | 'Controller' | 'Sales Manager' | 'Recon Manager' | 'Service Advisor' | 'Detail Team'
type ZoneStatus    = 'verified' | 'last-known' | 'unknown'

type RequestSource =
  | { type: 'person'; name: string; title: string; department: Department }
  | { type: 'system'; label: string }
  | { type: 'manual'; by: string }

interface RequestVehicle {
  stock: string; year: number; make: string; model: string; color: string
  zone: string; zoneStatus: ZoneStatus; zoneUpdatedLabel: string; daysInInventory: number
}

interface Request {
  id: string; type: RequestType; title: string; objective: string
  status: RequestStatus; source: RequestSource
  requestedBy: { name: string; title: string; department: Department }
  receivedLabel: string; lastUpdatedLabel: string
  minutesUntilDue: number | null; dueTimeLabel: string
  nextActionLabel: string; nextActionSub?: string
  vehicles: RequestVehicle[]; requestDetails?: string
  assignee?: string; dealerInfo?: { pickupLocation: string; returnDestination: string }
}

// ─── Data ─────────────────────────────────────────────────────────────────────

const REQUESTS: Request[] = [
  {
    id: 'r1', type: 'dealer-trade', title: 'Dealer Trade Pickup',
    objective: 'Dealer Trade — Sunrise Honda',
    status: 'new',
    source: { type: 'person', name: 'Rosa Pereira', title: 'Tower Manager', department: 'tower' },
    requestedBy: { name: 'Rosa Pereira', title: 'Tower Manager', department: 'tower' },
    receivedLabel: 'Received 2 min ago', lastUpdatedLabel: 'Just now',
    minutesUntilDue: -1, dueTimeLabel: 'ASAP',
    nextActionLabel: 'Drive to Sunrise Honda', nextActionSub: 'Off-site dealer trade · Return to LotSync Auto Group',
    dealerInfo: { pickupLocation: 'Sunrise Honda', returnDestination: 'LotSync Auto Group' },
    vehicles: [
      { stock: 'H72840', year: 2023, make: 'Subaru',  model: 'Outback', color: 'Crystal White',   zone: 'Offsite — Sunrise Honda', zoneStatus: 'last-known', zoneUpdatedLabel: '4h ago', daysInInventory: 18 },
      { stock: 'G19283', year: 2022, make: 'Toyota',  model: 'RAV4',    color: 'Magnetic Gray',    zone: 'Offsite — Sunrise Honda', zoneStatus: 'last-known', zoneUpdatedLabel: '4h ago', daysInInventory: 31 },
      { stock: 'B39281', year: 2024, make: 'Honda',   model: 'CR-V',    color: 'Sonic Gray Pearl', zone: 'Offsite — Sunrise Honda', zoneStatus: 'last-known', zoneUpdatedLabel: '4h ago', daysInInventory: 9  },
    ],
    requestDetails: 'Take dealer plates from the key cabinet. Bring the signed transfer paperwork from my desk — it\'s the blue folder. Confirm with Jordan before departing and text me when you\'re on the road. The contact at Sunrise is Mike T., call him when you arrive.',
  },
  {
    id: 'r2', type: 'locate', title: 'Locate Vehicle',
    objective: 'Inventory Audit — Missing VIN',
    status: 'new',
    source: { type: 'system', label: 'Inventory Sync' },
    requestedBy: { name: 'Sarah Kim', title: 'Controller', department: 'controller' },
    receivedLabel: 'Today · 8:03 AM', lastUpdatedLabel: '5 min ago',
    minutesUntilDue: -1, dueTimeLabel: 'ASAP',
    nextActionLabel: 'Locate this vehicle on the lot', nextActionSub: 'Not found during morning sync · Last seen Overflow Row C',
    vehicles: [
      { stock: 'P28192', year: 2021, make: 'Jeep', model: 'Grand Cherokee', color: 'Granite Crystal', zone: 'Last scan: Overflow Row C', zoneStatus: 'unknown', zoneUpdatedLabel: '6h ago', daysInInventory: 63 },
    ],
    requestDetails: 'Vehicle did not surface in this morning\'s sync. Walk the lot and confirm its physical location. Update zone in Tekion when found and mark this request complete.',
  },
  {
    id: 'r3', type: 'service-pull', title: 'Service Pull',
    objective: 'Scheduled Service Appointment',
    status: 'new',
    source: { type: 'person', name: 'Lisa Martinez', title: 'Service Advisor', department: 'service' },
    requestedBy: { name: 'Lisa Martinez', title: 'Service Advisor', department: 'service' },
    receivedLabel: 'Received 17 min ago', lastUpdatedLabel: '17 min ago',
    minutesUntilDue: 30, dueTimeLabel: '11:00 AM',
    nextActionLabel: 'Pull to Service Bay', nextActionSub: 'Stage at service bay entrance before 11:00 AM',
    vehicles: [
      { stock: 'E51388', year: 2023, make: 'BMW', model: '5 Series', color: 'Mineral White', zone: 'Premium Row', zoneStatus: 'verified', zoneUpdatedLabel: '12 min ago', daysInInventory: 7 },
    ],
    requestDetails: 'Customer arrives at 11:00 AM sharp. Vehicle must be staged at service bay entrance before they pull in. Keys are in Keyper under E51388.',
  },
  {
    id: 'r4', type: 'move-vehicle', title: 'Move to Showroom',
    objective: 'Sales Appointment — Customer Viewing',
    status: 'accepted',
    source: { type: 'person', name: 'Ben Wheeler', title: 'Sales Manager', department: 'sales' },
    requestedBy: { name: 'Ben Wheeler', title: 'Sales Manager', department: 'sales' },
    receivedLabel: 'Today · 9:41 AM', lastUpdatedLabel: '3 min ago',
    minutesUntilDue: 150, dueTimeLabel: '12:30 PM',
    nextActionLabel: 'Move to Showroom Floor', nextActionSub: 'Customer arrives at 1:00 PM · Wipe down before staging',
    vehicles: [
      { stock: 'A48291', year: 2023, make: 'Honda', model: 'Accord', color: 'Sonic Gray Pearl', zone: 'Kia Front Lot', zoneStatus: 'verified', zoneUpdatedLabel: '23 min ago', daysInInventory: 42 },
    ],
    assignee: 'Marcus Torres',
    requestDetails: 'Customer is coming in at 1:00 PM to view this vehicle. Have it inside, wiped down, and smelling clean. Stage it near the showroom entrance — first impression matters.',
  },
  {
    id: 'r5', type: 'delivery', title: 'Customer Delivery',
    objective: 'Pre-Delivery — Customer Pickup at 2:00 PM',
    status: 'new',
    source: { type: 'person', name: 'Lisa Martinez', title: 'Service Advisor', department: 'service' },
    requestedBy: { name: 'Lisa Martinez', title: 'Service Advisor', department: 'service' },
    receivedLabel: 'Today · 8:55 AM', lastUpdatedLabel: '42 min ago',
    minutesUntilDue: 210, dueTimeLabel: '1:45 PM',
    nextActionLabel: 'Prepare for Customer Delivery', nextActionSub: 'Fuel to full · Exterior wash · Stage at Delivery Bay 2',
    vehicles: [
      { stock: 'B93021', year: 2024, make: 'Toyota', model: 'Camry', color: 'Midnight Black', zone: 'Toyota Front Row', zoneStatus: 'verified', zoneUpdatedLabel: '8 min ago', daysInInventory: 14 },
    ],
    requestDetails: 'Fuel to full before pulling forward. Quick exterior wash. Stage at customer delivery bay 2 — have it ready 15 minutes before the customer arrives.',
  },
  {
    id: 'r6', type: 'showroom', title: 'Showroom Rotation',
    objective: 'Weekly Showroom Refresh',
    status: 'new',
    source: { type: 'person', name: 'Jordan Davis', title: 'Lot Manager', department: 'lot' },
    requestedBy: { name: 'Jordan Davis', title: 'Lot Manager', department: 'lot' },
    receivedLabel: 'Today · 9:15 AM', lastUpdatedLabel: '1h ago',
    minutesUntilDue: 270, dueTimeLabel: '3:00 PM',
    nextActionLabel: 'Move Vehicles to Showroom', nextActionSub: '2 vehicles · Wipe down before staging',
    vehicles: [
      { stock: 'D72044', year: 2024, make: 'Kia',  model: 'Telluride', color: 'Everest White',   zone: 'Kia Back Lot',  zoneStatus: 'verified', zoneUpdatedLabel: '31 min ago', daysInInventory: 22 },
      { stock: 'H64509', year: 2023, make: 'Mazda', model: 'CX-5',     color: 'Platinum Quartz', zone: 'Mazda Row',     zoneStatus: 'verified', zoneUpdatedLabel: '31 min ago', daysInInventory: 37 },
    ],
    requestDetails: 'Swap the two current showroom vehicles out following the floor plan on my desk. Both incoming vehicles should be wiped down before going in.',
  },
  {
    id: 'r7', type: 'fuel', title: 'Fuel for Delivery',
    objective: 'Pre-Delivery Preparation',
    status: 'assigned',
    source: { type: 'person', name: 'Jordan Davis', title: 'Lot Manager', department: 'lot' },
    requestedBy: { name: 'Jordan Davis', title: 'Lot Manager', department: 'lot' },
    receivedLabel: 'Today · 8:22 AM', lastUpdatedLabel: '8 min ago',
    minutesUntilDue: null, dueTimeLabel: '',
    nextActionLabel: 'Fuel Both Trucks', nextActionSub: 'Fuel cards in the lockbox · Service entrance',
    vehicles: [
      { stock: 'F29917', year: 2022, make: 'Chevrolet', model: 'Silverado', color: 'Black',        zone: 'Truck Row A', zoneStatus: 'verified',    zoneUpdatedLabel: '1h ago',  daysInInventory: 55 },
      { stock: 'C84711', year: 2022, make: 'Ford',      model: 'F-150',     color: 'Oxford White', zone: 'Truck Row B', zoneStatus: 'last-known', zoneUpdatedLabel: '3h ago',  daysInInventory: 47 },
    ],
    assignee: 'Marcus Torres',
    requestDetails: 'Both trucks need to be fueled to full before end of day. Fuel cards are in the lockbox near the service entrance.',
  },
  {
    id: 'r8', type: 'detail', title: 'Full Detail Before Delivery',
    objective: 'Pre-Delivery Detail',
    status: 'completed',
    source: { type: 'person', name: 'Ben Wheeler', title: 'Sales Manager', department: 'sales' },
    requestedBy: { name: 'Ben Wheeler', title: 'Sales Manager', department: 'sales' },
    receivedLabel: 'Yesterday · 4:37 PM', lastUpdatedLabel: '45 min ago',
    minutesUntilDue: null, dueTimeLabel: '',
    nextActionLabel: 'Detail the vehicle',
    vehicles: [
      { stock: 'G11203', year: 2024, make: 'Hyundai', model: 'Tucson', color: 'Shimmering Silver', zone: 'Hyundai Row', zoneStatus: 'verified', zoneUpdatedLabel: '45 min ago', daysInInventory: 28 },
    ],
    assignee: 'Detail Team',
    requestDetails: 'Full interior and exterior detail — not just a wipe. Customer picks up 9 AM tomorrow so this needs to be done tonight. Pay special attention to the cargo area.',
  },
]

// ─── Config ───────────────────────────────────────────────────────────────────

const statusCfg: Record<RequestStatus, { label: string; dot: string; text: string }> = {
  new:       { label: 'New',       dot: 'bg-blue-400',    text: 'text-blue-600'    },
  accepted:  { label: 'Accepted',  dot: 'bg-emerald-400', text: 'text-emerald-700' },
  assigned:  { label: 'Assigned',  dot: 'bg-violet-400',  text: 'text-violet-700'  },
  completed: { label: 'Completed', dot: 'bg-slate-300',   text: 'text-slate-500'   },
  cancelled: { label: 'Cancelled', dot: 'bg-slate-200',   text: 'text-slate-400'   },
}

const typeConfig: Record<RequestType, { label: string; color: string; icon: React.ReactNode }> = {
  'dealer-trade':  { label: 'Dealer Trade',     color: 'bg-orange-100 text-orange-600',   icon: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><rect x="1" y="3" width="15" height="13" rx="1" stroke="currentColor" strokeWidth="1.75"/><path d="M16 8h4l3 5v5h-7V8z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"/><circle cx="5.5" cy="18.5" r="2.5" stroke="currentColor" strokeWidth="1.75"/><circle cx="18.5" cy="18.5" r="2.5" stroke="currentColor" strokeWidth="1.75"/></svg> },
  'move-vehicle':  { label: 'Move Vehicle',     color: 'bg-blue-100 text-blue-600',       icon: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M5 12H19M13 6l6 6-6 6" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></svg> },
  'delivery':      { label: 'Customer Delivery',color: 'bg-emerald-100 text-emerald-600', icon: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"/></svg> },
  'showroom':      { label: 'Showroom',          color: 'bg-purple-100 text-purple-600',   icon: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"/><polyline points="9 22 9 12 15 12 15 22" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"/></svg> },
  'fuel':          { label: 'Fuel',              color: 'bg-yellow-100 text-yellow-700',   icon: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M3 22V6a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v16M3 11h11M17 9v6a2 2 0 0 0 4 0V9l-2-2" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></svg> },
  'detail':        { label: 'Detail',            color: 'bg-pink-100 text-pink-600',       icon: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.75"/><circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.75"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></svg> },
  'service-pull':  { label: 'Service Pull',      color: 'bg-slate-100 text-slate-600',     icon: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"/></svg> },
  'locate':        { label: 'Locate Vehicle',    color: 'bg-red-100 text-red-600',         icon: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"/><circle cx="12" cy="10" r="3" stroke="currentColor" strokeWidth="1.75"/></svg> },
  'custom':        { label: 'Custom',            color: 'bg-slate-100 text-slate-500',     icon: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"/><polyline points="14 2 14 8 20 8" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"/></svg> },
}

const deptColors: Record<Department, string> = {
  tower:      'bg-purple-50 text-purple-700 border-purple-100',
  sales:      'bg-emerald-50 text-emerald-700 border-emerald-100',
  service:    'bg-blue-50 text-blue-700 border-blue-100',
  recon:      'bg-orange-50 text-orange-700 border-orange-100',
  controller: 'bg-red-50 text-red-700 border-red-100',
  lot:        'bg-slate-100 text-slate-600 border-slate-200',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function isManager(role: AppRole) { return role !== 'Lot Staff' && role !== 'Detail Team' }

function urgencyRowCls(min: number | null) {
  if (min === -1 || (min !== null && min < 0)) return 'border-l-2 border-l-red-400'
  if (min !== null && min <= 60)               return 'border-l-2 border-l-orange-400'
  if (min !== null && min <= 180)              return 'border-l-2 border-l-amber-300'
  return ''
}

function nextActionUrgency(min: number | null): string {
  if (min === -1 || (min !== null && min < 0)) return 'bg-red-600 text-white'
  if (min !== null && min <= 60)               return 'bg-orange-500 text-white'
  if (min !== null && min <= 180)              return 'bg-amber-500 text-white'
  return 'bg-blue-600 text-white'
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SourceBadge({ source }: { source: RequestSource }) {
  if (source.type === 'system') return (
    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-blue-600 bg-blue-50 border border-blue-100 px-1.5 py-0.5 rounded-full">
      <svg width="8" height="8" fill="none" viewBox="0 0 24 24"><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" stroke="currentColor" strokeWidth="2.2"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-2.82 1.18V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" stroke="currentColor" strokeWidth="2.2"/></svg>
      {source.label}
    </span>
  )
  if (source.type === 'manual') return (
    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-slate-500 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded-full">
      <svg width="8" height="8" fill="none" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/></svg>
      {source.by}
    </span>
  )
  // person
  const dept = source.department.charAt(0).toUpperCase() + source.department.slice(1)
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full border ${deptColors[source.department]}`}>
      <svg width="8" height="8" fill="none" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"/><circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="2.2"/></svg>
      {dept}
    </span>
  )
}

function ConfidencePill({ status, label }: { status: ZoneStatus; label: string }) {
  const cfg = {
    verified:     { dot: 'bg-emerald-400', cls: 'text-emerald-700 bg-emerald-50 border-emerald-100', text: 'Verified' },
    'last-known': { dot: 'bg-amber-400',   cls: 'text-amber-700 bg-amber-50 border-amber-100',       text: 'Last Known' },
    unknown:      { dot: 'bg-red-400',     cls: 'text-red-700 bg-red-50 border-red-100',             text: 'Unknown' },
  }[status]
  return (
    <span className={`inline-flex items-center gap-1 text-[9px] font-bold px-1.5 py-0.5 rounded-full border ${cfg.cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.text} · {label}
    </span>
  )
}

function DeadlineIndicator({ min, dueTimeLabel }: { min: number | null; dueTimeLabel: string }) {
  if (min === null) return (
    <div className="flex items-center gap-2 py-1.5 px-3 bg-slate-50 border border-slate-100 rounded-xl">
      <span className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" />
      <span className="text-[12px] font-medium text-slate-500">No deadline</span>
    </div>
  )
  if (min === -1) return (
    <div className="flex items-center gap-2 py-1.5 px-3 bg-red-50 border border-red-200 rounded-xl">
      <span className="w-2 h-2 rounded-full bg-red-500 flex-shrink-0 animate-pulse" />
      <span className="text-[12px] font-bold text-red-700">ASAP — Urgent</span>
    </div>
  )
  if (min < 0) return (
    <div className="flex items-center gap-2 py-1.5 px-3 bg-red-50 border border-red-200 rounded-xl">
      <span className="w-2 h-2 rounded-full bg-red-500 flex-shrink-0" />
      <span className="text-[12px] font-bold text-red-700">Overdue by {Math.abs(min)} min</span>
      {dueTimeLabel && <span className="text-[10px] text-red-400 ml-auto">Was due {dueTimeLabel}</span>}
    </div>
  )
  if (min <= 30) return (
    <div className="flex items-center gap-2 py-1.5 px-3 bg-orange-50 border border-orange-200 rounded-xl">
      <span className="w-2 h-2 rounded-full bg-orange-500 flex-shrink-0" />
      <span className="text-[12px] font-bold text-orange-700">Due in {min} min</span>
      {dueTimeLabel && <span className="text-[10px] text-orange-400 ml-auto">By {dueTimeLabel}</span>}
    </div>
  )
  if (min <= 180) {
    const h = Math.floor(min / 60), m = min % 60
    return (
      <div className="flex items-center gap-2 py-1.5 px-3 bg-amber-50 border border-amber-200 rounded-xl">
        <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
        <span className="text-[12px] font-semibold text-amber-700">Due in {h > 0 ? `${h}h${m > 0 ? ` ${m}m` : ''}` : `${min} min`}</span>
        {dueTimeLabel && <span className="text-[10px] text-amber-500 ml-auto">By {dueTimeLabel}</span>}
      </div>
    )
  }
  return (
    <div className="flex items-center gap-2 py-1.5 px-3 bg-slate-50 border border-slate-100 rounded-xl">
      <span className="w-2 h-2 rounded-full bg-slate-300 flex-shrink-0" />
      <span className="text-[12px] font-medium text-slate-600">Due by {dueTimeLabel}</span>
    </div>
  )
}

function NextActionBanner({ r }: { r: Request }) {
  if (r.status === 'completed' || r.status === 'cancelled') return null
  const cls = nextActionUrgency(r.minutesUntilDue)
  return (
    <div className={`rounded-xl px-4 py-3 ${cls}`}>
      <div className="flex items-center gap-2 mb-0.5">
        <svg width="13" height="13" fill="none" viewBox="0 0 24 24" className="opacity-80 flex-shrink-0">
          <path d="M5 12H19M13 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span className="text-[13px] font-bold leading-tight">{r.nextActionLabel}</span>
      </div>
      {r.nextActionSub && <p className="text-[11px] opacity-75 leading-snug pl-5">{r.nextActionSub}</p>}
    </div>
  )
}

function CollapsibleText({ text, name, receivedLabel, avatarInitials }: { text: string; name: string; receivedLabel: string; avatarInitials: string }) {
  const [open, setOpen] = useState(false)
  const THRESHOLD = 160
  const long = text.length > THRESHOLD
  const displayed = open || !long ? text : text.slice(0, THRESHOLD).trimEnd() + '…'
  return (
    <div>
      <div className="flex items-start gap-2.5">
        <div className="w-7 h-7 rounded-full bg-violet-600 flex items-center justify-center text-white text-[10px] font-bold flex-shrink-0 mt-0.5">{avatarInitials}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-[11px] font-bold text-slate-700">{name}</span>
            <span className="text-[10px] text-slate-400">{receivedLabel}</span>
          </div>
          <div className="bg-slate-50 border border-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 text-[13px] text-slate-700 leading-relaxed">
            {displayed}
            {long && (
              <button onClick={() => setOpen(o => !o)}
                className="ml-1.5 text-[11px] font-bold text-blue-500 hover:text-blue-700 transition-colors inline-flex items-center gap-0.5">
                {open ? 'Show less ▲' : 'Show more ▼'}
              </button>
            )}
          </div>
        </div>
      </div>
      {/* Thread affordance */}
      <div className="pl-9 mt-4">
        <div className="border border-dashed border-slate-200 rounded-2xl px-4 py-3 flex items-center gap-3">
          <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-white text-[9px] font-bold flex-shrink-0">MT</div>
          <div className="flex-1">
            <div className="text-[11px] text-slate-300 select-none">Reply to {name.split(' ')[0]}…</div>
          </div>
          <span className="text-[9px] font-bold text-slate-300 uppercase tracking-wider">Coming soon</span>
        </div>
      </div>
    </div>
  )
}

function DealerTradeRoute({ info, vehicles }: { info: NonNullable<Request['dealerInfo']>; vehicles: RequestVehicle[] }) {
  return (
    <div className="bg-orange-50 border border-orange-100 rounded-xl p-4">
      <div className="text-[9px] font-bold text-orange-400 uppercase tracking-widest mb-3">Off-Site Route</div>
      <div className="flex gap-3 items-stretch">
        <div className="flex flex-col items-center pt-1 pb-1">
          <div className="w-6 h-6 rounded-full bg-white border-2 border-orange-300 flex items-center justify-center flex-shrink-0">
            <svg width="10" height="10" fill="none" viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" stroke="#f97316" strokeWidth="2" strokeLinejoin="round"/><circle cx="12" cy="10" r="3" stroke="#f97316" strokeWidth="2"/></svg>
          </div>
          <div className="w-px flex-1 bg-orange-200 my-1.5" />
          <div className="w-6 h-6 rounded-full bg-white border-2 border-orange-300 flex items-center justify-center flex-shrink-0">
            <svg width="10" height="10" fill="none" viewBox="0 0 24 24"><rect x="1" y="3" width="15" height="13" rx="1" stroke="#f97316" strokeWidth="1.75"/><path d="M16 8h4l3 5v5h-7V8z" stroke="#f97316" strokeWidth="1.75" strokeLinejoin="round"/></svg>
          </div>
          <div className="w-px flex-1 bg-orange-200 my-1.5" />
          <div className="w-6 h-6 rounded-full bg-white border-2 border-orange-300 flex items-center justify-center flex-shrink-0">
            <svg width="10" height="10" fill="none" viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" stroke="#f97316" strokeWidth="1.75" strokeLinejoin="round"/></svg>
          </div>
        </div>
        <div className="flex flex-col justify-between gap-2 flex-1 min-w-0">
          <div><div className="text-[9px] font-bold text-orange-400 uppercase tracking-wider">Pickup From</div><div className="text-[13px] font-bold text-slate-800">{info.pickupLocation}</div></div>
          <div><div className="flex items-center gap-1.5"><span className="text-[9px] font-bold text-orange-400 uppercase tracking-wider">Transport</span><span className="text-[9px] font-bold bg-orange-200 text-orange-700 px-1.5 py-0.5 rounded-full">{vehicles.length} vehicle{vehicles.length !== 1 ? 's' : ''}</span></div><div className="text-[11px] text-slate-500">Drive to return destination</div></div>
          <div><div className="text-[9px] font-bold text-orange-400 uppercase tracking-wider">Return To</div><div className="text-[13px] font-bold text-slate-800">{info.returnDestination}</div></div>
        </div>
      </div>
    </div>
  )
}

function VehicleCard({ v, onSelect }: { v: RequestVehicle; onSelect: () => void }) {
  return (
    <button onClick={onSelect}
      className="w-full bg-white border border-slate-100 rounded-xl p-3.5 text-left hover:border-blue-200 hover:shadow-sm hover:-translate-y-px transition-all duration-150 group cursor-pointer">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-[11px] font-bold text-blue-600 group-hover:underline">Stock #{v.stock}</span>
          <ConfidencePill status={v.zoneStatus} label={v.zoneUpdatedLabel} />
        </div>
        <svg width="10" height="10" fill="none" viewBox="0 0 24 24" className="text-slate-200 group-hover:text-blue-400 transition-colors flex-shrink-0">
          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <div className="text-[13px] font-bold text-slate-900 mb-1.5">{v.year} {v.make} {v.model}</div>
      <div className="flex items-center gap-2.5 flex-wrap text-[11px] text-slate-500">
        <span>{v.color}</span>
        <span className="text-slate-200">·</span>
        <div className="flex items-center gap-1">
          <svg width="9" height="9" fill="none" viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/><circle cx="12" cy="10" r="3" stroke="currentColor" strokeWidth="2"/></svg>
          <span>{v.zone}</span>
        </div>
        <span className="text-slate-200">·</span>
        <span className={v.daysInInventory >= 45 ? 'text-amber-600 font-semibold' : ''}>{v.daysInInventory}d in inventory</span>
      </div>
    </button>
  )
}

// ─── Empty state ──────────────────────────────────────────────────────────────

type InboxFilter = 'inbox' | 'mine' | 'accepted' | 'completed' | 'archived'

const emptyStates: Record<InboxFilter, { title: string; body: string; icon: React.ReactNode }> = {
  inbox: {
    title: 'Inbox Zero',
    body: 'No outstanding requests right now.',
    icon: <svg width="28" height="28" fill="none" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" stroke="#86efac" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  },
  mine: {
    title: 'Nothing assigned to you',
    body: "You don't have any accepted requests.",
    icon: <svg width="28" height="28" fill="none" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="#94a3b8" strokeWidth="1.75" strokeLinecap="round"/><circle cx="12" cy="7" r="4" stroke="#94a3b8" strokeWidth="1.75"/></svg>,
  },
  accepted: {
    title: 'No accepted requests',
    body: 'Accept a request from the inbox to see it here.',
    icon: <svg width="28" height="28" fill="none" viewBox="0 0 24 24"><path d="M9 11l3 3L22 4" stroke="#94a3b8" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" stroke="#94a3b8" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  },
  completed: {
    title: 'Nothing completed yet',
    body: 'Requests completed today will appear here.',
    icon: <svg width="28" height="28" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" stroke="#94a3b8" strokeWidth="1.75"/><path d="m9 12 2 2 4-4" stroke="#94a3b8" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  },
  archived: {
    title: 'Archive is empty',
    body: 'Declined and cancelled requests will appear here.',
    icon: <svg width="28" height="28" fill="none" viewBox="0 0 24 24"><path d="M21 8v13H3V8M1 3h22v5H1zM10 12h4" stroke="#94a3b8" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  },
}

function EmptyState({ filter }: { filter: InboxFilter }) {
  const e = emptyStates[filter]
  return (
    <div className="flex flex-col items-center justify-center h-48 px-6 text-center">
      <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mb-3">{e.icon}</div>
      <div className="text-[13px] font-bold text-slate-600 mb-1">{e.title}</div>
      <div className="text-[11px] text-slate-400 leading-snug">{e.body}</div>
    </div>
  )
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function matchesFilter(r: Request, inbox: InboxFilter, dept: Department | 'all'): boolean {
  const deptOk = dept === 'all' || r.requestedBy.department === dept
  if (!deptOk) return false
  if (inbox === 'inbox')     return r.status === 'new'
  if (inbox === 'mine')      return r.assignee === 'Marcus Torres'
  if (inbox === 'accepted')  return r.status === 'accepted' || r.status === 'assigned'
  if (inbox === 'completed') return r.status === 'completed'
  if (inbox === 'archived')  return r.status === 'cancelled'
  return true
}

function Sidebar({ inbox, dept, onInbox, onDept }: {
  inbox: InboxFilter; dept: Department | 'all'
  onInbox: (f: InboxFilter) => void; onDept: (d: Department | 'all') => void
}) {
  const count = (f: InboxFilter) => REQUESTS.filter(r => matchesFilter(r, f, 'all')).length
  const depts: { label: string; value: Department }[] = [
    { label: 'Tower',      value: 'tower'      },
    { label: 'Sales',      value: 'sales'      },
    { label: 'Service',    value: 'service'    },
    { label: 'Recon',      value: 'recon'      },
    { label: 'Controller', value: 'controller' },
  ]

  function NavBtn({ label, f, warn }: { label: string; f: InboxFilter; warn?: boolean }) {
    const c = count(f); const on = inbox === f && dept === 'all'
    return (
      <button onClick={() => { onInbox(f); onDept('all') }}
        className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all ${on ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}>
        {label}
        {c > 0 && <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${on ? 'bg-white/20' : warn ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-500'}`}>{c}</span>}
      </button>
    )
  }

  return (
    <aside className="flex-shrink-0 w-44 bg-white border-r border-slate-200 flex flex-col py-3 overflow-y-auto" style={{ scrollbarWidth: 'none' }}>
      <div className="text-[9px] font-bold uppercase tracking-widest text-slate-400 px-3 pb-1">Inbox</div>
      <div className="px-2 space-y-0.5 mb-4">
        <NavBtn label="Inbox"          f="inbox"     warn />
        <NavBtn label="Assigned to Me" f="mine"      />
        <NavBtn label="Accepted"       f="accepted"  />
        <NavBtn label="Completed"      f="completed" />
        <NavBtn label="Archived"       f="archived"  />
      </div>
      <div className="text-[9px] font-bold uppercase tracking-widest text-slate-400 px-3 pb-1">Department</div>
      <div className="px-2 space-y-0.5">
        {depts.map(d => {
          const c = REQUESTS.filter(r => r.requestedBy.department === d.value && r.status === 'new').length
          const on = dept === d.value
          return (
            <button key={d.value} onClick={() => { onDept(on ? 'all' : d.value); onInbox('inbox') }}
              className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all ${on ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}>
              {d.label}
              {c > 0 && <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${on ? 'bg-white/20' : 'bg-slate-100 text-slate-500'}`}>{c}</span>}
            </button>
          )
        })}
      </div>
    </aside>
  )
}

// ─── Center list row ──────────────────────────────────────────────────────────

function RequestRow({ r, selected, onSelect }: { r: Request; selected: boolean; onSelect: () => void }) {
  const tc = typeConfig[r.type]; const sc = statusCfg[r.status]
  const v0 = r.vehicles[0]; const extra = r.vehicles.length - 1

  function DueTag() {
    const min = r.minutesUntilDue
    if (min === null) return null
    if (min === -1)         return <span className="text-[10px] font-bold text-red-600">ASAP</span>
    if (min < 0)            return <span className="text-[10px] font-bold text-red-600">Overdue</span>
    if (min <= 60)          return <span className="text-[10px] font-bold text-orange-600">{min}m</span>
    if (min <= 180)         return <span className="text-[10px] font-semibold text-amber-600">{r.dueTimeLabel}</span>
    return <span className="text-[10px] text-slate-400">{r.dueTimeLabel}</span>
  }

  return (
    <button onClick={onSelect}
      className={`w-full text-left px-3 py-2.5 border-b border-slate-100 transition-all ${urgencyRowCls(r.minutesUntilDue)} ${selected ? 'bg-blue-50' : 'hover:bg-slate-50'}`}>
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="flex items-center gap-2 min-w-0">
          <div className={`w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 ${tc.color}`}>{tc.icon}</div>
          <span className={`text-[12.5px] font-semibold truncate ${selected ? 'text-blue-700' : 'text-slate-900'}`}>{r.title}</span>
        </div>
        <DueTag />
      </div>
      <div className="pl-7 space-y-0.5">
        <div className="flex items-center gap-1.5">
          <span className="text-[10.5px] text-slate-400">{r.requestedBy.name}</span>
          <SourceBadge source={r.source} />
          <div className="flex items-center gap-1 ml-auto flex-shrink-0">
            <span className={`w-1.5 h-1.5 rounded-full ${sc.dot}`} />
            <span className={`text-[10px] font-semibold ${sc.text}`}>{sc.label}</span>
          </div>
        </div>
        {v0 && (
          <div className="text-[10px] text-slate-400">
            <span className="font-mono font-bold text-slate-500">{v0.stock}</span>
            <span> · {v0.year} {v0.make} {v0.model}</span>
            {extra > 0 && <span className="text-slate-300"> +{extra}</span>}
          </div>
        )}
      </div>
    </button>
  )
}

// ─── Activity footer ──────────────────────────────────────────────────────────

function ActivityFooter({ r }: { r: Request }) {
  const srcLabel = r.source.type === 'system' ? r.source.label
    : r.source.type === 'manual' ? r.source.by
    : `${r.source.name}, ${r.source.title}`
  return (
    <div className="px-1 py-3 border-t border-slate-100 mt-1">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-slate-400">
        <span>Created by <span className="text-slate-500 font-medium">{r.requestedBy.name}</span></span>
        <span className="text-slate-200">·</span>
        <span>{r.receivedLabel}</span>
        <span className="text-slate-200">·</span>
        <span>Updated {r.lastUpdatedLabel}</span>
        <span className="text-slate-200">·</span>
        <span>Source: <span className="text-slate-500 font-medium">{srcLabel}</span></span>
      </div>
    </div>
  )
}

// ─── Detail pane ──────────────────────────────────────────────────────────────

function DetailPane({ r, role, onVehicleSelect, onStatusChange }: {
  r: Request; role: AppRole; onVehicleSelect: (s: string) => void
  onStatusChange: (id: string, s: RequestStatus) => void
}) {
  const [vehicleExpanded, setVehicleExpanded] = useState(false)
  const [transitioning, setTransitioning] = useState(false)
  const [transitionLabel, setTransitionLabel] = useState('')

  // Reset expansion when request changes
  useEffect(() => { setVehicleExpanded(false) }, [r.id])

  const tc  = typeConfig[r.type]
  const sc  = statusCfg[r.status]
  const mgr = isManager(role)
  const ini = (n: string) => n.split(' ').map(w => w[0]).join('')

  const SHOW_FIRST = 3
  const shownVehicles = vehicleExpanded ? r.vehicles : r.vehicles.slice(0, SHOW_FIRST)
  const hiddenCount   = r.vehicles.length - SHOW_FIRST

  function handleStatus(s: RequestStatus, label: string) {
    setTransitioning(true); setTransitionLabel(label)
    setTimeout(() => { onStatusChange(r.id, s); setTransitioning(false) }, 600)
  }

  function Actions() {
    if (transitioning) return (
      <div className="flex items-center gap-2 text-[12px] font-semibold text-slate-500">
        <span className="w-4 h-4 rounded-full border-2 border-slate-300 border-t-blue-500 animate-spin" />
        {transitionLabel}
      </div>
    )
    if (r.status === 'new') return mgr ? (
      <div className="flex gap-2">
        <button onClick={() => handleStatus('accepted', 'Accepting…')} className="text-[12px] font-bold px-4 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Accept</button>
        <button onClick={() => handleStatus('assigned', 'Assigning…')} className="text-[12px] font-semibold px-4 py-1.5 bg-white text-slate-700 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors">Assign</button>
        <button onClick={() => handleStatus('cancelled', 'Declining…')} className="text-[12px] text-slate-400 hover:text-red-600 transition-colors px-2">Decline</button>
      </div>
    ) : (
      <div className="flex gap-2">
        <button onClick={() => handleStatus('accepted', 'Accepting request…')} className="text-[12px] font-bold px-4 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Accept Request</button>
        <button onClick={() => handleStatus('cancelled', 'Declining…')} className="text-[12px] text-slate-400 hover:text-red-600 transition-colors px-2">Decline</button>
      </div>
    )
    if (r.status === 'accepted' || r.status === 'assigned') {
      const assignedToMe = r.assignee === 'Marcus Torres'
      return (
        <div className="flex items-center gap-3">
          {assignedToMe && <span className="flex items-center gap-1.5 text-[11px] font-bold text-emerald-600 bg-emerald-50 border border-emerald-100 px-2.5 py-1 rounded-full"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />Assigned to You</span>}
          {mgr ? (
            <>
              <button onClick={() => handleStatus('completed', 'Marking complete…')} className="text-[12px] font-bold px-4 py-1.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors">Mark Completed</button>
              <button className="text-[12px] font-semibold px-3 py-1.5 bg-white text-slate-600 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors">Reassign</button>
              <button onClick={() => handleStatus('cancelled', 'Cancelling…')} className="text-[12px] text-slate-400 hover:text-red-600 transition-colors px-1">Cancel</button>
            </>
          ) : (
            <button onClick={() => handleStatus('completed', 'Marking done…')} className="text-[12px] font-bold px-4 py-1.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors">Mark Done</button>
          )}
        </div>
      )
    }
    if (r.status === 'completed') return <span className="flex items-center gap-1.5 text-[12px] text-emerald-600 font-semibold"><svg width="13" height="13" fill="none" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/></svg>Completed</span>
    if (r.status === 'cancelled') return <span className="text-[12px] text-slate-400">This request was cancelled</span>
    return null
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden min-h-0 bg-slate-50">
      {/* Sticky header */}
      <div className="flex-shrink-0 bg-white border-b border-slate-200 px-6 pt-4 pb-3">
        <div className="flex items-start gap-3 mb-3">
          <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5 ${tc.color}`}>{tc.icon}</div>
          <div className="flex-1 min-w-0">
            <h2 className="text-[17px] font-bold text-slate-900 leading-tight">{r.title}</h2>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              <span className={`w-1.5 h-1.5 rounded-full ${sc.dot}`} />
              <span className={`text-[11px] font-semibold ${sc.text}`}>{sc.label}</span>
              <SourceBadge source={r.source} />
              <span className="text-[10px] text-slate-400">{r.receivedLabel}</span>
            </div>
          </div>
        </div>
        <Actions />
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3" style={{ scrollbarWidth: 'thin' }}>

        {/* 1 — Next action (primary) */}
        <NextActionBanner r={r} />

        {/* 2 — Request info card */}
        <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
          {/* Objective */}
          <div className="px-5 pt-4 pb-3 border-b border-slate-50">
            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Objective</div>
            <div className="text-[15px] font-bold text-slate-900 leading-snug">{r.objective}</div>
          </div>
          {/* Deadline */}
          <div className="px-5 py-3 border-b border-slate-50">
            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-2">Deadline</div>
            <DeadlineIndicator min={r.minutesUntilDue} dueTimeLabel={r.dueTimeLabel} />
          </div>
          {/* Requester */}
          <div className="px-5 py-3">
            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-2">Requested By</div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-violet-600 flex items-center justify-center text-white text-[11px] font-bold flex-shrink-0">{ini(r.requestedBy.name)}</div>
              <div>
                <div className="text-[13px] font-bold text-slate-900">{r.requestedBy.name}</div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[11px] text-slate-500">{r.requestedBy.title}</span>
                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-md border ${deptColors[r.requestedBy.department]}`}>
                    {r.requestedBy.department.charAt(0).toUpperCase() + r.requestedBy.department.slice(1)}
                  </span>
                </div>
              </div>
            </div>
            {r.assignee && (
              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-50">
                <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Assigned To</span>
                <span className="text-[12px] font-semibold text-slate-700">{r.assignee}</span>
              </div>
            )}
          </div>
        </div>

        {/* 3 — Vehicles */}
        {r.vehicles.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
            <div className="px-5 pt-4 pb-3">
              <div className="flex items-center justify-between mb-3">
                <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">
                  {r.vehicles.length > 1 ? `Vehicles (${r.vehicles.length})` : 'Vehicle'}
                </div>
                {hiddenCount > 0 && (
                  <button onClick={() => setVehicleExpanded(e => !e)}
                    className="text-[10px] font-bold text-blue-500 hover:text-blue-700 transition-colors flex items-center gap-1">
                    {vehicleExpanded ? 'Collapse ▲' : `Show ${hiddenCount} more vehicle${hiddenCount > 1 ? 's' : ''} ▼`}
                  </button>
                )}
              </div>
              {r.dealerInfo && <div className="mb-3"><DealerTradeRoute info={r.dealerInfo} vehicles={r.vehicles} /></div>}
              <div className="space-y-2">
                {shownVehicles.map(v => <VehicleCard key={v.stock} v={v} onSelect={() => onVehicleSelect(v.stock)} />)}
              </div>
            </div>
          </div>
        )}

        {/* 4 — Request Details */}
        {r.requestDetails && (
          <div className="bg-white rounded-2xl border border-slate-100 px-5 pt-4 pb-4">
            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-3">Request Details</div>
            <CollapsibleText
              text={r.requestDetails}
              name={r.requestedBy.name}
              receivedLabel={r.receivedLabel}
              avatarInitials={ini(r.requestedBy.name)}
            />
          </div>
        )}

        {/* 5 — Lifecycle (footer weight) + Activity */}
        <div className="px-1">
          <div className="flex items-center gap-2 mb-3">
            {(['new', 'accepted', 'completed'] as RequestStatus[]).map((step, i, arr) => {
              const labels: Partial<Record<RequestStatus, string>> = { new: 'New', accepted: 'Accepted', completed: 'Completed' }
              const order: RequestStatus[] = ['new', 'accepted', 'assigned', 'completed']
              const done = r.status !== 'cancelled' && order.indexOf(r.status) >= order.indexOf(step)
              return (
                <div key={step} className="flex items-center gap-2">
                  <div className={`flex items-center gap-1 text-[10px] font-medium ${done ? 'text-slate-500' : 'text-slate-300'}`}>
                    <span className={`w-3 h-3 rounded-full flex items-center justify-center ${done ? 'bg-slate-300' : 'bg-slate-100'}`}>
                      {done && <svg width="6" height="6" fill="none" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" stroke="white" strokeWidth="4" strokeLinecap="round"/></svg>}
                    </span>
                    {labels[step]}
                  </div>
                  {i < arr.length - 1 && <svg width="8" height="8" fill="none" viewBox="0 0 24 24"><path d="m9 18 6-6-6-6" stroke={done ? '#cbd5e1' : '#e2e8f0'} strokeWidth="2.5" strokeLinecap="round"/></svg>}
                </div>
              )
            })}
          </div>
          <ActivityFooter r={r} />
        </div>

      </div>
    </div>
  )
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function Requests({ role, onVehicleSelect }: { role: AppRole; onVehicleSelect: (s: string) => void }) {
  const [inbox,      setInbox]      = useState<InboxFilter>('inbox')
  const [dept,       setDept]       = useState<Department | 'all'>('all')
  const [selectedId, setSelectedId] = useState<string | null>(REQUESTS[0]?.id ?? null)
  const [statuses,   setStatuses]   = useState<Record<string, RequestStatus>>({})

  const getStatus = (r: Request): RequestStatus => statuses[r.id] ?? r.status

  const visible = REQUESTS
    .map(r => ({ ...r, status: getStatus(r) }))
    .filter(r => matchesFilter(r, inbox, dept))

  const selectedRequest =
    visible.find(r => r.id === selectedId) ??
    REQUESTS.map(r => ({ ...r, status: getStatus(r) })).find(r => r.id === selectedId)

  return (
    <div className="flex-1 flex overflow-hidden min-h-0">
      <Sidebar inbox={inbox} dept={dept} onInbox={setInbox} onDept={setDept} />

      {/* Center list */}
      <div className="flex-shrink-0 flex flex-col overflow-hidden border-r border-slate-200 bg-white min-w-0" style={{ width: 'clamp(220px, 22vw, 290px)' }}>
        <div className="flex-shrink-0 flex items-center justify-between px-3 py-2.5 border-b border-slate-200">
          <span className="text-[11.5px] font-bold text-slate-700">
            {{ inbox: 'Inbox', mine: 'Assigned to Me', accepted: 'Accepted', completed: 'Completed', archived: 'Archived' }[inbox]}
          </span>
          <span className="text-[10px] text-slate-400 font-medium">{visible.length}</span>
        </div>
        <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
          {visible.length === 0
            ? <EmptyState filter={inbox} />
            : visible.map(r => <RequestRow key={r.id} r={r} selected={selectedId === r.id} onSelect={() => setSelectedId(r.id)} />)
          }
        </div>
      </div>

      {/* Detail pane */}
      {selectedRequest ? (
        <DetailPane
          key={selectedRequest.id}
          r={selectedRequest}
          role={role}
          onVehicleSelect={onVehicleSelect}
          onStatusChange={(id, s) => setStatuses(p => ({ ...p, [id]: s }))}
        />
      ) : (
        <div className="flex-1 flex items-center justify-center bg-slate-50">
          <div className="text-center text-slate-400">
            <svg width="32" height="32" fill="none" viewBox="0 0 24 24" className="mx-auto mb-2 opacity-25"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/></svg>
            <p className="text-[12px] font-medium">Select a request</p>
          </div>
        </div>
      )}
    </div>
  )
}
