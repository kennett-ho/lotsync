import { useState, useRef, type ReactNode } from 'react'
import QuickLog from '../components/QuickLog'

// ─── Types ────────────────────────────────────────────────────────────────────

type UploadStatus = 'idle' | 'uploading' | 'done' | 'error'
type TaskPriority = 'Critical' | 'High' | 'Medium' | 'Low'
type SyncStatus = 'idle' | 'running' | 'done'
type DayPhase = 'morning' | 'midday' | 'eod'
type TaskOrigin = 'automated' | 'management'

const priorityMeta: Record<TaskPriority, { bg: string; text: string; dot: string }> = {
  Critical: { bg: 'bg-red-50', text: 'text-red-600', dot: 'bg-red-500' },
  High: { bg: 'bg-orange-50', text: 'text-orange-600', dot: 'bg-orange-500' },
  Medium: { bg: 'bg-amber-50', text: 'text-amber-600', dot: 'bg-amber-400' },
  Low: { bg: 'bg-slate-100', text: 'text-slate-500', dot: 'bg-slate-400' },
}

// ─── Data ─────────────────────────────────────────────────────────────────────

const upcomingWork: {
  id: string; title: string; stock: string; vehicle: string
  priority: TaskPriority; origin: TaskOrigin; eta: string; requestedBy?: string
}[] = [
  { id: 't2', title: 'Install MDD Device', stock: 'B93021', vehicle: '2022 Ford F-150 XLT', priority: 'High', origin: 'automated', eta: '20 min' },
  { id: 't3', title: 'Replace Stock Tag', stock: 'C84711', vehicle: '2021 Chevrolet Malibu 2LT', priority: 'Medium', origin: 'automated', eta: '5 min' },
  { id: 't7', title: 'Install RecovR', stock: 'M48302', vehicle: '2023 Tesla Model 3 LR', priority: 'Medium', origin: 'automated', eta: '15 min' },
  { id: 't4', title: 'Fuel Vehicle', stock: 'G10923', vehicle: '2023 Lexus ES 350', priority: 'Low', origin: 'management', eta: '10 min', requestedBy: 'K. Davis' },
  { id: 't5', title: 'Dealer Trade Pickup', stock: 'H72840', vehicle: '2022 Honda Civic Sport', priority: 'High', origin: 'management', eta: '25 min', requestedBy: 'K. Davis' },
  { id: 't6', title: 'Move to Showroom', stock: 'N20381', vehicle: '2023 Audi A6 Premium', priority: 'Medium', origin: 'management', eta: '8 min', requestedBy: 'J. Davis' },
]

const eodCompletedWork = [
  { title: 'Installed 4 RecovR devices', time: '10:12 AM' },
  { title: 'Replaced 3 stock tags', time: '11:04 AM' },
  { title: 'Moved 6 vehicles to staging', time: '12:30 PM' },
  { title: 'Completed dealer trade pickup', time: '2:15 PM' },
  { title: 'Fueled 2 vehicles', time: '3:40 PM' },
  { title: 'Customer delivery prep complete', time: '4:22 PM' },
  { title: 'Moved vehicle to showroom', time: '5:01 PM' },
  { title: 'Damage report logged on Stock L83042', time: '5:44 PM' },
]

const eodRemaining = [
  { title: 'Install MDD Device', stock: 'B93021', priority: 'High' as TaskPriority },
  { title: 'Fuel Vehicle', stock: 'G10923', priority: 'Low' as TaskPriority },
  { title: 'Install RecovR', stock: 'M48302', priority: 'Medium' as TaskPriority },
]

const systems = [
  { id: 'tekion', name: 'Tekion', desc: 'DMS export report' },
  { id: 'keyper', name: 'Keyper', desc: 'Key transaction log' },
  { id: 'recovr', name: 'RecovR', desc: 'Device manifest' },
  { id: 'mdd', name: 'MDD', desc: 'Beacon status report' },
  { id: 'rapidrecon', name: 'RapidRecon', desc: 'Recon workflow export' },
]

const dispatchRequests = [
  { id: 'r1', type: 'Dealer Trade', urgent: true, title: 'Pickup at Sunrise Honda', vehicle: 'Stock F38102 · 2021 Ford F-150', from: 'Jordan Davis', time: '8:15 AM', eta: 'ASAP' },
  { id: 'r2', type: 'Customer Delivery', urgent: false, title: 'Prep for 2 PM delivery', vehicle: 'Stock T29017 · 2022 Toyota Corolla', from: 'Ben Wheeler (Sales)', time: '7:55 AM', eta: 'By 1:30 PM' },
  { id: 'r3', type: 'Pull Vehicle', urgent: false, title: 'Test drive pull — front lot', vehicle: 'Stock P11928 · 2022 Nissan Altima SV', from: 'Ben Wheeler (Sales)', time: '8:22 AM', eta: '30 min' },
]

const liveActivity = [
  { time: '8:16 AM', text: 'Accepted Dealer Trade — Stock F38102', type: 'info' },
  { time: '7:58 AM', text: 'Moved to staging — Stock L83042', type: 'success' },
  { time: '7:41 AM', text: 'Completed RecovR install — Stock P11928', type: 'success' },
  { time: '7:22 AM', text: 'Started fueling — Stock G10923', type: 'info' },
  { time: '6:58 AM', text: 'Inventory Sync complete — 1,247 vehicles processed', type: 'success' },
  { time: '6:47 AM', text: 'Uploaded Keyper report', type: 'info' },
]

const reqTypeMeta: Record<string, { bg: string; text: string }> = {
  'Dealer Trade': { bg: 'bg-violet-50', text: 'text-violet-700' },
  'Customer Delivery': { bg: 'bg-blue-50', text: 'text-blue-700' },
  'Pull Vehicle': { bg: 'bg-slate-100', text: 'text-slate-600' },
}

// ─── Icons ────────────────────────────────────────────────────────────────────

const Ic = {
  check: <svg width="11" height="11" fill="none" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  upload: <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  spinner: <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.2"/><path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/></svg>,
  car: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M5 17H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h13l4 4v4a2 2 0 0 1-2 2h-2M5 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0zM15 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round"/></svg>,
  arrow: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  error: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.75"/><path d="M15 9l-6 6M9 9l6 6" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></svg>,
  external: <svg width="11" height="11" fill="none" viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  dots: <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><circle cx="5" cy="12" r="1.5" fill="currentColor"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/><circle cx="19" cy="12" r="1.5" fill="currentColor"/></svg>,
  sun: <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5" stroke="currentColor" strokeWidth="1.75"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></svg>,
  midday: <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><path d="M17 21H7M12 3v1M4.22 7.22l.71.71M1 12h1M2.93 16.78l.71-.71M21.07 7.22l-.71.71M23 12h-1M21.07 16.78l-.71-.71" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/><path d="M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16z" stroke="currentColor" strokeWidth="1.75"/></svg>,
  moon: <svg width="13" height="13" fill="none" viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  checkCircle: <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/><path d="M22 4 12 14.01l-3-3" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  refresh: <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M23 4v6h-6M1 20v-6h6" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  pin: <svg width="11" height="11" fill="none" viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" stroke="currentColor" strokeWidth="1.75"/><circle cx="12" cy="10" r="3" stroke="currentColor" strokeWidth="1.75"/></svg>,
  clock: <svg width="11" height="11" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.75"/><path d="M12 6v6l4 2" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></svg>,
}

// ─── Phase Banner ─────────────────────────────────────────────────────────────

function PhaseBanner({ phase, onChange }: { phase: DayPhase; onChange: (p: DayPhase) => void }) {
  const config: Record<DayPhase, { label: string; sub: string; bg: string; border: string; dot: string }> = {
    morning: { label: 'Morning Operations', sub: 'Run Inventory Sync before starting assignments', bg: 'bg-amber-50', border: 'border-amber-200', dot: 'bg-amber-400' },
    midday: { label: 'Midday Operations', sub: 'Work through your task queue', bg: 'bg-blue-50', border: 'border-blue-200', dot: 'bg-blue-400' },
    eod: { label: 'End-of-Day Review', sub: 'Operational summary for today', bg: 'bg-violet-50', border: 'border-violet-200', dot: 'bg-violet-400' },
  }
  const c = config[phase]

  return (
    <div className={`flex items-center justify-between px-4 py-2.5 rounded-xl border ${c.bg} ${c.border}`}>
      <div className="flex items-center gap-2.5">
        <span className={`w-2 h-2 rounded-full ${c.dot}`} />
        <span className="text-[12px] font-bold text-slate-700">{c.label}</span>
        <span className="text-[11px] text-slate-400">·</span>
        <span className="text-[11px] text-slate-500">{c.sub}</span>
        <span className="text-[10px] text-slate-400 bg-white/70 border border-slate-200 px-1.5 py-0.5 rounded font-medium ml-1">Demo</span>
      </div>
      <div className="flex items-center gap-1 bg-white/80 rounded-lg p-0.5 border border-white">
        {([
          { id: 'morning' as DayPhase, icon: Ic.sun, label: 'AM' },
          { id: 'midday' as DayPhase, icon: Ic.midday, label: 'PM' },
          { id: 'eod' as DayPhase, icon: Ic.moon, label: 'EOD' },
        ]).map(p => (
          <button key={p.id} onClick={() => onChange(p.id)}
            className={`flex items-center gap-1 text-[10px] font-bold px-2.5 py-1 rounded-md transition-all ${
              phase === p.id ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}>
            {p.icon} {p.label}
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── StockPill ────────────────────────────────────────────────────────────────

function StockPill({ stock, onSelect }: { stock: string; onSelect: (s: string) => void }) {
  return (
    <button onClick={() => onSelect(stock)}
      className="font-mono text-[11px] font-bold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-1.5 py-0.5 rounded transition-colors">
      {stock}
    </button>
  )
}

// ─── Greeting ─────────────────────────────────────────────────────────────────

function Greeting({ phase }: { phase: DayPhase }) {
  const greetings: Record<DayPhase, string> = { morning: 'Good Morning', midday: 'Good Afternoon', eod: 'Good Evening' }
  const subtext: Record<DayPhase, ReactNode> = {
    morning: <p className="text-[13px] text-slate-500 mt-1">Wednesday, July 23 · <span className="text-amber-600 font-semibold">Inventory Sync required before assignments begin</span></p>,
    midday: <p className="text-[13px] text-slate-500 mt-1">Wednesday, July 23 · <span className="text-slate-700 font-semibold">8 tasks remaining</span> · <span className="text-blue-600 font-semibold">2 open requests</span></p>,
    eod: <p className="text-[13px] text-slate-500 mt-1">Wednesday, July 23 · <span className="text-emerald-600 font-semibold">8 of 11 tasks completed</span> · 3 remaining</p>,
  }
  const stats: Record<DayPhase, { label: string; value: string; color: string }[]> = {
    morning: [
      { label: 'Tasks Assigned', value: '11', color: 'text-blue-600' },
      { label: 'Open Requests', value: '3', color: 'text-slate-700' },
    ],
    midday: [
      { label: 'Tasks Completed', value: '3', color: 'text-emerald-600' },
      { label: 'Remaining', value: '8', color: 'text-slate-700' },
    ],
    eod: [
      { label: 'Tasks Completed', value: '8', color: 'text-emerald-600' },
      { label: 'Remaining', value: '3', color: 'text-amber-600' },
    ],
  }

  return (
    <div className="flex items-start justify-between">
      <div>
        <h1 className="text-[26px] font-bold text-slate-900 tracking-tight">{greetings[phase]}, Marcus</h1>
        {subtext[phase]}
      </div>
      <div className="flex items-center gap-4">
        {stats[phase].map(s => (
          <div key={s.label} className="text-right">
            <div className="text-[12px] font-semibold text-slate-500">{s.label}</div>
            <div className={`text-[20px] font-bold tabular-nums ${s.color}`}>{s.value}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Current Assignment ───────────────────────────────────────────────────────

function CurrentAssignment({ onVehicleSelect, phase }: { onVehicleSelect: (s: string) => void; phase: DayPhase }) {
  if (phase === 'morning') {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <div className="h-1 w-full bg-slate-200" />
        <div className="p-5 flex flex-col items-center justify-center gap-3 py-10 text-center">
          <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center">
            <span className="text-slate-400">{Ic.car}</span>
          </div>
          <div>
            <div className="text-[15px] font-bold text-slate-700">No assignment yet</div>
            <div className="text-[12px] text-slate-400 mt-1">Complete Inventory Sync to receive your first assignment</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
      <div className="h-1 w-full bg-gradient-to-r from-blue-600 via-blue-500 to-blue-400" />
      <div className="p-5">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-blue-600">Current Assignment</span>
              <span className="flex items-center gap-1 text-[10px] font-bold text-orange-600 bg-orange-50 border border-orange-200 px-1.5 py-0.5 rounded">
                <span className="w-1 h-1 rounded-full bg-orange-500" /> High Priority
              </span>
            </div>
            <h2 className="text-[24px] font-bold text-slate-900 tracking-tight leading-none">Install RecovR</h2>
          </div>
          <div className="text-right flex-shrink-0">
            <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-0.5">Est. Duration</div>
            <div className="text-[22px] font-bold text-slate-800 tabular-nums">15 min</div>
          </div>
        </div>

        <div className="mb-4">
          <div className="flex justify-between text-[10px] text-slate-400 mb-1">
            <span>Progress</span><span>In Progress</span>
          </div>
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 rounded-full" style={{ width: '35%' }} />
          </div>
        </div>

        <div className="flex items-center gap-4 p-3.5 bg-slate-50 rounded-xl border border-slate-100 mb-4">
          <div className="w-9 h-9 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0">
            <span className="text-blue-600">{Ic.car}</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[14px] font-bold text-slate-900">2023 Honda Accord EX-L</div>
            <div className="flex items-center gap-2 mt-0.5">
              <StockPill stock="A48291" onSelect={onVehicleSelect} />
              <span className="font-mono text-[11px] text-slate-400">…004352</span>
            </div>
          </div>
          <div className="text-right flex-shrink-0">
            <div className="flex items-center gap-1 text-[10px] text-slate-400 justify-end mb-0.5">
              {Ic.pin} Location
            </div>
            <div className="text-[12px] font-bold text-slate-700">Row 4, Space 12</div>
          </div>
        </div>

        {/* Dependency placeholder — reserved for future */}
        <div className="hidden items-center gap-2 px-3.5 py-2.5 bg-amber-50 border border-amber-200 rounded-lg mb-4 text-[12px] text-amber-700 font-semibold">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
          Waiting on keys
        </div>

        <div className="flex gap-2.5">
          <button className="flex-1 h-10 bg-blue-600 hover:bg-blue-700 text-white text-[13px] font-bold rounded-xl transition-colors flex items-center justify-center gap-2">
            Continue Task <span>{Ic.arrow}</span>
          </button>
          <button onClick={() => onVehicleSelect('A48291')}
            className="h-10 px-4 bg-slate-50 hover:bg-slate-100 text-slate-700 text-[13px] font-semibold rounded-xl border border-slate-200 hover:border-slate-300 transition-all">
            View Vehicle
          </button>
          <button className="w-10 h-10 bg-slate-50 hover:bg-slate-100 text-slate-500 rounded-xl border border-slate-200 hover:border-slate-300 transition-all flex items-center justify-center">
            {Ic.dots}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Upcoming Work ────────────────────────────────────────────────────────────

function TaskRow({ task, onVehicleSelect, onSkip }: {
  task: typeof upcomingWork[0]; onVehicleSelect: (s: string) => void; onSkip?: () => void
}) {
  const pm = priorityMeta[task.priority]
  return (
    <div className="flex items-center gap-3.5 px-5 py-3 hover:bg-slate-50 transition-colors group">
      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${pm.dot}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-[13px] font-bold text-slate-900 truncate">{task.title}</span>
          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded flex-shrink-0 ${pm.bg} ${pm.text}`}>{task.priority}</span>
        </div>
        <div className="flex items-center gap-2">
          <StockPill stock={task.stock} onSelect={onVehicleSelect} />
          <span className="text-[11px] text-slate-400 truncate">{task.vehicle}</span>
        </div>
      </div>
      <div className="flex items-center gap-3 flex-shrink-0">
        <div className="text-right">
          <div className="flex items-center gap-1 text-[11px] font-semibold text-slate-600 justify-end">
            {Ic.clock} {task.eta}
          </div>
          {task.requestedBy && <div className="text-[10px] text-slate-400">{task.requestedBy}</div>}
        </div>
        <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
          <button className="text-[11px] font-bold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-2.5 py-1 rounded-lg transition-colors">Start</button>
          {onSkip && (
            <button onClick={onSkip}
              className="text-[11px] font-bold text-slate-400 hover:text-slate-600 bg-slate-50 hover:bg-slate-100 border border-slate-200 px-2 py-1 rounded-lg transition-colors">
              Skip
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function SectionHeader({ label, count, origin }: { label: string; count: number; origin: TaskOrigin }) {
  const colors: Record<TaskOrigin, string> = {
    automated: 'text-blue-600 bg-blue-50',
    management: 'text-violet-600 bg-violet-50',
  }
  return (
    <div className="flex items-center gap-2 px-5 py-2 bg-slate-50 border-y border-slate-100">
      <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${colors[origin]}`}>{label}</span>
      <span className="text-[10px] text-slate-400">{count} tasks</span>
    </div>
  )
}

function UpcomingWork({ onVehicleSelect, phase }: { onVehicleSelect: (s: string) => void; phase: DayPhase }) {
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  if (phase === 'eod') {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <h3 className="text-[14px] font-bold text-slate-900">Remaining Tasks</h3>
            <span className="text-[11px] font-bold text-amber-600 bg-amber-50 border border-amber-100 px-2 py-0.5 rounded-full">{eodRemaining.length}</span>
          </div>
        </div>
        <div className="divide-y divide-slate-50">
          {eodRemaining.map((task) => {
            const pm = priorityMeta[task.priority]
            return (
              <div key={task.stock} className="flex items-center gap-3.5 px-5 py-3 hover:bg-slate-50 transition-colors group">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${pm.dot}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[13px] font-bold text-slate-700 truncate">{task.title}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${pm.bg} ${pm.text} flex-shrink-0`}>{task.priority}</span>
                  </div>
                  <StockPill stock={task.stock} onSelect={onVehicleSelect} />
                </div>
                <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                  <button className="text-[11px] font-bold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-2.5 py-1 rounded-lg transition-colors">View</button>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  const automatedItems = upcomingWork.filter(t => t.origin === 'automated' && !dismissed.has(t.id))
  const managementItems = upcomingWork.filter(t => t.origin === 'management' && !dismissed.has(t.id))
  const totalCount = automatedItems.length + managementItems.length

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <h3 className="text-[14px] font-bold text-slate-900">Upcoming Work</h3>
          <span className="text-[11px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">{totalCount}</span>
        </div>
      </div>

      {automatedItems.length > 0 && (
        <>
          <SectionHeader label="Automated" count={automatedItems.length} origin="automated" />
          <div className="divide-y divide-slate-50">
            {automatedItems.map(task => (
              <TaskRow key={task.id} task={task} onVehicleSelect={onVehicleSelect}
                onSkip={() => setDismissed(d => new Set(d).add(task.id))} />
            ))}
          </div>
        </>
      )}

      {managementItems.length > 0 && (
        <>
          <SectionHeader label="Management Requests" count={managementItems.length} origin="management" />
          <div className="divide-y divide-slate-50">
            {managementItems.map(task => (
              <TaskRow key={task.id} task={task} onVehicleSelect={onVehicleSelect}
                onSkip={() => setDismissed(d => new Set(d).add(task.id))} />
            ))}
          </div>
        </>
      )}

      {totalCount === 0 && (
        <div className="flex flex-col items-center justify-center py-10 text-slate-400">
          <span className="text-3xl mb-2">🎉</span>
          <p className="text-[13px] font-semibold">Queue is clear</p>
        </div>
      )}
    </div>
  )
}

// ─── Inventory Sync ───────────────────────────────────────────────────────────

function InventorySync({ phase }: { phase: DayPhase }) {
  const [states, setStates] = useState<Record<string, UploadStatus>>({
    tekion: 'idle', keyper: 'done', recovr: 'idle', mdd: 'idle', rapidrecon: 'idle'
  })
  const [sync, setSync] = useState<SyncStatus>('idle')
  const [results] = useState({ processed: 1247, tasks: 18, recs: 5, exceptions: 23, secs: 102 })
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({})

  // EOD: always show completed
  const effectiveSync = phase === 'eod' ? 'done' : sync

  const handleUpload = (id: string) => {
    setStates(p => ({ ...p, [id]: 'uploading' }))
    setTimeout(() => setStates(p => ({ ...p, [id]: 'done' })), 1200 + Math.random() * 800)
  }

  const allUploaded = Object.values(states).every(s => s === 'done')

  const handleRunSync = () => {
    setSync('running')
    setTimeout(() => setSync('done'), 2800)
  }

  const handleRunAgain = () => {
    setSync('idle')
    setStates({ tekion: 'idle', keyper: 'idle', recovr: 'idle', mdd: 'idle', rapidrecon: 'idle' })
  }

  // Completed state
  if (effectiveSync === 'done') {
    return (
      <div className="bg-white rounded-2xl border border-emerald-200 overflow-hidden">
        <div className="h-1 w-full bg-emerald-400" />
        <div className="p-4">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-emerald-500">{Ic.checkCircle}</span>
            <span className="text-[13px] font-bold text-slate-900">Inventory Sync Complete</span>
          </div>
          <div className="flex items-center gap-3 mb-3">
            <span className="text-[10px] text-slate-400 font-mono">Last run: 7:08 AM · {Math.floor(results.secs / 60)}m {results.secs % 60}s</span>
            <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded-full ml-auto">Current</span>
          </div>

          <div className="grid grid-cols-2 gap-2 mb-3">
            {[
              { label: 'Vehicles Processed', value: results.processed.toLocaleString(), color: 'text-slate-900' },
              { label: 'Tasks Created', value: results.tasks, color: 'text-blue-600' },
              { label: 'Recommendations', value: results.recs, color: 'text-violet-600' },
              { label: 'Exceptions Found', value: results.exceptions, color: 'text-amber-600' },
            ].map(r => (
              <div key={r.label} className="bg-slate-50 border border-slate-100 rounded-xl px-3 py-2.5">
                <div className={`text-[18px] font-bold ${r.color}`}>{r.value}</div>
                <div className="text-[10px] text-slate-400">{r.label}</div>
              </div>
            ))}
          </div>

          <div className="flex gap-2">
            <button className="flex-1 h-9 bg-slate-900 hover:bg-slate-800 text-white text-[12px] font-bold rounded-xl transition-colors flex items-center justify-center gap-1.5">
              View Results <span>{Ic.external}</span>
            </button>
            <button onClick={handleRunAgain}
              className="h-9 px-3.5 bg-slate-50 hover:bg-slate-100 text-slate-600 text-[12px] font-semibold border border-slate-200 hover:border-slate-300 rounded-xl transition-all flex items-center gap-1.5">
              {Ic.refresh} Run Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Running state
  if (sync === 'running') {
    return (
      <div className="bg-white rounded-2xl border border-blue-200 overflow-hidden">
        <div className="h-1 w-full bg-blue-400 animate-pulse" />
        <div className="p-5 flex flex-col items-center gap-3 py-8">
          <span className="text-blue-500 animate-spin">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.2"/><path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/></svg>
          </span>
          <div className="text-center">
            <div className="text-[14px] font-bold text-slate-900">Running Inventory Sync…</div>
            <div className="text-[12px] text-slate-400 mt-1">Processing 1,247 vehicles across 5 systems</div>
          </div>
          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 rounded-full animate-pulse" style={{ width: '65%' }} />
          </div>
        </div>
      </div>
    )
  }

  // Upload state
  const isMorningFocus = phase === 'morning'
  const pendingCount = Object.values(states).filter(s => s !== 'done').length

  return (
    <div className={`bg-white rounded-2xl overflow-hidden ${isMorningFocus ? 'border-2 border-blue-300 shadow-md shadow-blue-100' : 'border border-slate-200'}`}>
      {isMorningFocus && <div className="h-1 w-full bg-gradient-to-r from-blue-600 to-blue-400" />}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-[14px] font-bold text-slate-900">Inventory Sync</h3>
            {isMorningFocus && (
              <span className="text-[10px] font-bold text-blue-700 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded-full">Start here</span>
            )}
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">Upload system reports to begin sync</p>
        </div>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
          allUploaded ? 'text-emerald-600 bg-emerald-50 border-emerald-200' : 'text-amber-700 bg-amber-50 border-amber-200'
        }`}>
          {allUploaded ? 'Ready to Run' : 'Sync Required'}
        </span>
      </div>

      <div className="divide-y divide-slate-50">
        {systems.map(sys => {
          const st = states[sys.id]
          return (
            <div key={sys.id} className="flex items-center gap-3 px-5 py-3">
              <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                st === 'done' ? 'bg-emerald-100' : st === 'uploading' ? 'bg-blue-100' : st === 'error' ? 'bg-red-100' : 'bg-slate-100'
              }`}>
                {st === 'done' && <span className="text-emerald-600">{Ic.check}</span>}
                {st === 'uploading' && <span className="text-blue-600 animate-spin inline-block">{Ic.spinner}</span>}
                {st === 'error' && <span className="text-red-600">{Ic.error}</span>}
                {st === 'idle' && <span className="text-slate-400">{Ic.upload}</span>}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[13px] font-bold text-slate-900">{sys.name}</div>
                <div className="text-[11px] text-slate-400">{sys.desc}</div>
              </div>
              <div className="flex-shrink-0">
                {st === 'done' && <span className="text-[11px] font-semibold text-emerald-600">Uploaded</span>}
                {st === 'uploading' && <span className="text-[11px] font-semibold text-blue-600">Uploading…</span>}
                {st === 'error' && (
                  <button onClick={() => handleUpload(sys.id)} className="text-[11px] font-bold text-red-600 hover:text-red-700 bg-red-50 border border-red-200 px-2.5 py-1 rounded-lg transition-colors">Retry</button>
                )}
                {st === 'idle' && (
                  <>
                    <input type="file" ref={el => { fileRefs.current[sys.id] = el }} className="hidden" onChange={() => handleUpload(sys.id)} />
                    <button onClick={() => handleUpload(sys.id)}
                      className="text-[11px] font-bold text-slate-600 hover:text-blue-600 bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-300 px-2.5 py-1 rounded-lg transition-all flex items-center gap-1.5">
                      {Ic.upload} Upload
                    </button>
                  </>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <div className="px-5 py-4 border-t border-slate-100 bg-slate-50/60">
        <button onClick={handleRunSync} disabled={!allUploaded}
          className={`w-full h-10 rounded-xl text-[13px] font-bold transition-all ${
            allUploaded ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:shadow-md' : 'bg-slate-200 text-slate-400 cursor-not-allowed'
          }`}>
          {allUploaded ? 'Run Inventory Sync' : `Upload Reports — ${pendingCount} remaining`}
        </button>
      </div>
    </div>
  )
}

// ─── Operational Stats ────────────────────────────────────────────────────────

function OpsStats({ phase }: { phase: DayPhase }) {
  const statsByPhase: Record<DayPhase, { label: string; value: string; color: string }[]> = {
    morning: [
      { label: 'Tasks Assigned', value: '11', color: 'text-blue-600' },
      { label: 'Open Requests', value: '3', color: 'text-slate-900' },
      { label: 'Inventory Synced', value: '—', color: 'text-slate-400' },
      { label: 'Exceptions', value: '—', color: 'text-slate-400' },
    ],
    midday: [
      { label: 'Tasks Completed', value: '3', color: 'text-emerald-600' },
      { label: 'Remaining', value: '8', color: 'text-slate-900' },
      { label: 'Open Requests', value: '2', color: 'text-blue-600' },
      { label: 'Exceptions', value: '23', color: 'text-amber-600' },
    ],
    eod: [
      { label: 'Tasks Completed', value: '8', color: 'text-emerald-600' },
      { label: 'Remaining', value: '3', color: 'text-amber-600' },
      { label: 'Open Requests', value: '0', color: 'text-slate-400' },
      { label: 'Vehicles Synced', value: '1,247', color: 'text-blue-600' },
    ],
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {statsByPhase[phase].map(s => (
        <div key={s.label} className="bg-white rounded-xl border border-slate-200 px-4 py-3 hover:shadow-sm transition-shadow">
          <div className={`text-[22px] font-bold ${s.color}`}>{s.value}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">{s.label}</div>
        </div>
      ))}
    </div>
  )
}

// ─── EOD Progress Summary ─────────────────────────────────────────────────────

function EODProgress({ onVehicleSelect }: { onVehicleSelect: (s: string) => void }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <div className="h-1 w-full bg-gradient-to-r from-emerald-500 to-blue-500" />
      <div className="px-5 pt-4 pb-3 border-b border-slate-100">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[14px] font-bold text-slate-900">Today's Progress</h3>
          <span className="text-[11px] font-bold text-emerald-600 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">8 of 11 complete</span>
        </div>
        <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden mb-1.5">
          <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-blue-500" style={{ width: '73%' }} />
        </div>
        <div className="flex justify-between text-[10px] text-slate-400">
          <span>73% of tasks complete</span>
          <span>3 remaining</span>
        </div>
      </div>

      <div className="px-5 py-3 border-b border-slate-50">
        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Completed today</div>
        <div className="space-y-1.5">
          {eodCompletedWork.map((item, i) => (
            <div key={i} className="flex items-center gap-2.5">
              <span className="text-emerald-500 flex-shrink-0">{Ic.check}</span>
              <span className="text-[12px] text-slate-700 flex-1 truncate">{item.title}</span>
              <span className="text-[10px] font-mono text-slate-400 flex-shrink-0">{item.time}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="px-5 py-3">
        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Still remaining</div>
        <div className="space-y-1.5">
          {eodRemaining.map((item, i) => {
            const pm = priorityMeta[item.priority]
            return (
              <div key={i} className="flex items-center gap-2.5">
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${pm.dot}`} />
                <span className="text-[12px] text-slate-600 flex-1">{item.title}</span>
                <StockPill stock={item.stock} onSelect={onVehicleSelect} />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ─── Requests ─────────────────────────────────────────────────────────────────

function Requests({ phase }: { phase: DayPhase }) {
  const [handled, setHandled] = useState<Set<string>>(new Set())
  const visible = dispatchRequests.filter(r => !handled.has(r.id))
  const effective = phase === 'eod' ? [] : visible

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <h3 className="text-[14px] font-bold text-slate-900">Requests</h3>
          {effective.length > 0 && (
            <span className="text-[10px] font-bold text-white bg-blue-600 px-1.5 py-0.5 rounded-full">{effective.length}</span>
          )}
        </div>
        <span className="text-[11px] text-slate-400">From people</span>
      </div>

      <div className="divide-y divide-slate-50">
        {effective.map(req => {
          const tm = reqTypeMeta[req.type] ?? { bg: 'bg-slate-100', text: 'text-slate-600' }
          return (
            <div key={req.id} className={`px-5 py-3.5 hover:bg-slate-50 transition-colors ${req.urgent ? 'border-l-2 border-red-400' : ''}`}>
              <div className="flex items-start justify-between gap-3 mb-2">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${tm.bg} ${tm.text}`}>{req.type}</span>
                    {req.urgent && <span className="text-[10px] font-bold text-red-600 animate-pulse">Urgent</span>}
                    <span className="text-[10px] text-slate-400">{req.time}</span>
                  </div>
                  <p className="text-[13px] font-bold text-slate-900">{req.title}</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">{req.vehicle}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-[11px] font-semibold text-slate-700">{req.from}</div>
                  <div className="text-[10px] text-amber-600 font-semibold">{req.eta}</div>
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => setHandled(h => new Set(h).add(req.id))}
                  className="flex-1 h-8 bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-bold rounded-lg transition-colors">Accept</button>
                <button onClick={() => setHandled(h => new Set(h).add(req.id))}
                  className="h-8 px-3 bg-slate-50 hover:bg-slate-100 text-slate-500 text-[11px] font-semibold border border-slate-200 rounded-lg transition-colors">Decline</button>
              </div>
            </div>
          )
        })}

        {effective.length === 0 && (
          <div className="flex flex-col items-center justify-center py-5 text-slate-400">
            <p className="text-[12px] font-semibold">No pending requests</p>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Verification Needed ──────────────────────────────────────────────────────

type VerifyStatus = 'waiting' | 'verified' | 'investigating'

const verificationItems: {
  id: string; label: string; stock: string; vehicle: string
  loggedAt: string; status: VerifyStatus
}[] = [
  { id: 'v1', label: 'RecovR Installed',   stock: 'A48291', vehicle: '2023 Honda Accord EX-L',   loggedAt: '7:41 AM', status: 'waiting' },
  { id: 'v2', label: 'MDD Installed',       stock: 'B93021', vehicle: '2022 Ford F-150 XLT',      loggedAt: '6:58 AM', status: 'investigating' },
  { id: 'v3', label: 'Stock Tag Replaced',  stock: 'C84711', vehicle: '2021 Chevrolet Malibu 2LT', loggedAt: '6:20 AM', status: 'verified' },
]

const verifyMeta: Record<VerifyStatus, { dot: string; label: string; text: string; bg: string; border: string }> = {
  waiting:       { dot: 'bg-amber-400',  label: 'Waiting',        text: 'text-amber-700', bg: 'bg-amber-50',  border: 'border-amber-200' },
  verified:      { dot: 'bg-emerald-500',label: 'Verified',        text: 'text-emerald-700', bg: 'bg-emerald-50',  border: 'border-emerald-200' },
  investigating: { dot: 'bg-red-500',    label: 'Needs attention', text: 'text-red-700',   bg: 'bg-red-50',    border: 'border-red-200' },
}

function VerificationNeeded({ onVehicleSelect }: { onVehicleSelect: (s: string) => void }) {
  const waiting = verificationItems.filter(i => i.status === 'waiting').length
  const issues  = verificationItems.filter(i => i.status === 'investigating').length

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      {/* Accent strip — amber when there are open items, slate when all clear */}
      <div className={`h-0.5 w-full ${issues > 0 ? 'bg-red-400' : waiting > 0 ? 'bg-amber-400' : 'bg-emerald-400'}`} />

      <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <h3 className="text-[14px] font-bold text-slate-900">Verification Needed</h3>
          {(waiting + issues) > 0 && (
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
              issues > 0 ? 'text-red-600 bg-red-50 border border-red-200' : 'text-amber-700 bg-amber-50 border border-amber-200'
            }`}>
              {waiting + issues} pending
            </span>
          )}
        </div>
        <span className="text-[10px] text-slate-400">Confirmed by Inventory Sync</span>
      </div>

      {/* Lifecycle hint */}
      <div className="flex items-center gap-2 px-5 py-2.5 bg-slate-50/60 border-b border-slate-100">
        {(['Logged', 'Waiting', 'Sync', 'Verified'] as const).map((label, i, arr) => (
          <div key={label} className="flex items-center gap-2">
            <span className={`text-[10px] font-semibold ${
              label === 'Logged' ? 'text-blue-600' :
              label === 'Waiting' ? 'text-amber-600' :
              label === 'Sync' ? 'text-slate-500' :
              'text-emerald-600'
            }`}>{label}</span>
            {i < arr.length - 1 && (
              <svg width="10" height="10" fill="none" viewBox="0 0 24 24" className="text-slate-300 flex-shrink-0">
                <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
          </div>
        ))}
      </div>

      <div className="divide-y divide-slate-50">
        {verificationItems.map(item => {
          const m = verifyMeta[item.status]
          return (
            <div key={item.id} className="flex items-center gap-3.5 px-5 py-3 hover:bg-slate-50 transition-colors group">
              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${m.dot} ${item.status === 'waiting' ? 'animate-pulse' : ''}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-[13px] font-bold text-slate-900">{item.label}</span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${m.bg} ${m.text} border ${m.border} flex-shrink-0`}>
                    {m.label}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => onVehicleSelect(item.stock)}
                    className="font-mono text-[11px] font-bold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-1.5 py-0.5 rounded transition-colors">
                    {item.stock}
                  </button>
                  <span className="text-[11px] text-slate-400 truncate">{item.vehicle}</span>
                </div>
                {item.status === 'waiting' && (
                  <p className="text-[10px] text-slate-400 mt-0.5">Logged {item.loggedAt} · Waiting for next Inventory Sync</p>
                )}
                {item.status === 'investigating' && (
                  <p className="text-[10px] text-red-500 font-semibold mt-0.5">Still appears in today's system report — review needed</p>
                )}
                {item.status === 'verified' && (
                  <p className="text-[10px] text-emerald-600 mt-0.5">Confirmed during latest Inventory Sync</p>
                )}
              </div>
              {item.status === 'investigating' && (
                <button className="opacity-0 group-hover:opacity-100 transition-opacity text-[11px] font-bold text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 px-2.5 py-1 rounded-lg flex-shrink-0">
                  Review
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── Live Activity ────────────────────────────────────────────────────────────

function LiveActivity() {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-3.5 border-b border-slate-100">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
        <h3 className="text-[14px] font-bold text-slate-900">Live Activity</h3>
      </div>
      <div className="divide-y divide-slate-50">
        {liveActivity.map((item, i) => (
          <div key={i} className="flex gap-3 px-5 py-2.5 hover:bg-slate-50 transition-colors">
            <div className="flex flex-col items-center pt-1 flex-shrink-0">
              <span className={`w-1.5 h-1.5 rounded-full ${item.type === 'success' ? 'bg-emerald-400' : 'bg-blue-400'}`} />
              {i < liveActivity.length - 1 && <div className="w-px flex-1 bg-slate-100 mt-1" style={{ minHeight: '12px' }} />}
            </div>
            <div className="flex-1 min-w-0 pb-1">
              <div className="text-[10px] font-mono text-slate-400 mb-0.5">{item.time}</div>
              <div className="text-[12px] text-slate-700">{item.text}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Right Column ─────────────────────────────────────────────────────────────

function RightColumn({ phase, onVehicleSelect }: { phase: DayPhase; onVehicleSelect: (s: string) => void }) {
  if (phase === 'eod') {
    return (
      <div className="space-y-4">
        <EODProgress onVehicleSelect={onVehicleSelect} />
        <InventorySync phase={phase} />
        <OpsStats phase={phase} />
        <VerificationNeeded onVehicleSelect={onVehicleSelect} />
        <LiveActivity />
      </div>
    )
  }

  if (phase === 'morning') {
    return (
      <div className="space-y-4">
        <InventorySync phase={phase} />
        <OpsStats phase={phase} />
        <LiveActivity />
      </div>
    )
  }

  // Midday
  return (
    <div className="space-y-4">
      <InventorySync phase={phase} />
      <OpsStats phase={phase} />
      <VerificationNeeded onVehicleSelect={onVehicleSelect} />
      <Requests phase={phase} />
      <LiveActivity />
    </div>
  )
}

// ─── Lot Staff Dashboard ──────────────────────────────────────────────────────

export default function LotStaffDashboard({ onVehicleSelect }: { onVehicleSelect: (s: string) => void }) {
  const autoPhase = (): DayPhase => {
    const h = new Date().getHours()
    if (h < 10) return 'morning'
    if (h < 16) return 'midday'
    return 'eod'
  }

  const [phase, setPhase] = useState<DayPhase>(autoPhase)

  return (
    <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5 pb-24" style={{ scrollbarWidth: 'thin' }}>
      <PhaseBanner phase={phase} onChange={setPhase} />
      <Greeting phase={phase} />

      <div className="grid gap-5" style={{ gridTemplateColumns: '1fr 380px' }}>
        <div className="space-y-4">
          <CurrentAssignment onVehicleSelect={onVehicleSelect} phase={phase} />
          <UpcomingWork onVehicleSelect={onVehicleSelect} phase={phase} />
          {phase === 'morning' && <Requests phase={phase} />}
        </div>
        <div>
          <RightColumn phase={phase} onVehicleSelect={onVehicleSelect} />
        </div>
      </div>

      <QuickLog onVehicleSelect={onVehicleSelect} />
    </div>
  )
}
