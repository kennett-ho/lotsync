import { useState } from 'react'

type ExceptionType = 'Missing from DMS' | 'Not Found on Lot' | 'Duplicate VIN' | 'Price Discrepancy' | 'Missing Title'
type ExceptionStatus = 'Open' | 'Under Review' | 'Pending Approval' | 'Resolved'

const exTypeMeta: Record<ExceptionType, { bg: string; text: string }> = {
  'Missing from DMS': { bg: 'bg-red-50', text: 'text-red-700' },
  'Not Found on Lot': { bg: 'bg-orange-50', text: 'text-orange-700' },
  'Duplicate VIN': { bg: 'bg-violet-50', text: 'text-violet-700' },
  'Price Discrepancy': { bg: 'bg-amber-50', text: 'text-amber-700' },
  'Missing Title': { bg: 'bg-slate-100', text: 'text-slate-600' },
}

const exStatusMeta: Record<ExceptionStatus, { bg: string; text: string }> = {
  Open: { bg: 'bg-red-50', text: 'text-red-600' },
  'Under Review': { bg: 'bg-blue-50', text: 'text-blue-700' },
  'Pending Approval': { bg: 'bg-amber-50', text: 'text-amber-700' },
  Resolved: { bg: 'bg-emerald-50', text: 'text-emerald-700' },
}

const exceptions = [
  { id: 'e1', vin: '1HGCM82633A004352', stock: 'A48291', make: 'Honda', model: 'Accord EX-L', type: 'Not Found on Lot' as ExceptionType, days: 3, status: 'Open' as ExceptionStatus, assignedTo: 'S. Kim', note: 'Vehicle missing from Row 4 – beacon not pinging' },
  { id: 'e2', vin: '2T1BURHE0JC036571', stock: 'T29017', make: 'Toyota', model: 'Corolla LE', type: 'Missing from DMS' as ExceptionType, days: 2, status: 'Under Review' as ExceptionStatus, assignedTo: 'S. Kim', note: 'Present on lot, not appearing in Tekion' },
  { id: 'e3', vin: '5YJ3E1EA0JF006261', stock: 'M48302', make: 'Tesla', model: 'Model 3 LR', type: 'Price Discrepancy' as ExceptionType, days: 1, status: 'Pending Approval' as ExceptionStatus, assignedTo: 'S. Kim', note: 'Listed $48,900 in Tekion vs $46,500 in physical sticker' },
  { id: 'e4', vin: 'WAUYGAFC5CN004752', stock: 'N20381', make: 'Audi', model: 'A6 Premium', type: 'Missing Title' as ExceptionType, days: 8, status: 'Open' as ExceptionStatus, assignedTo: 'Unassigned', note: 'Title not received from previous owner – 8 days overdue' },
  { id: 'e5', vin: '1G1ZT53806F109890', stock: 'C84711', make: 'Chevrolet', model: 'Malibu 2LT', type: 'Duplicate VIN' as ExceptionType, days: 1, status: 'Open' as ExceptionStatus, assignedTo: 'S. Kim', note: 'VIN appears on both Stock C84711 and K32045' },
  { id: 'e6', vin: '1FTEW1E53JKD03928', stock: 'F38102', make: 'Ford', model: 'F-150 XLT', type: 'Missing from DMS' as ExceptionType, days: 5, status: 'Under Review' as ExceptionStatus, assignedTo: 'S. Kim', note: 'Vehicle sold but not closed in Tekion' },
]

const auditQueue = [
  { id: 'a1', type: 'Sold Vehicle Approval', vehicle: '2022 Toyota Corolla LE · Stock T29017', submittedBy: 'Ben Wheeler (Sales)', time: '8:02 AM', priority: 'High' },
  { id: 'a2', type: 'Placeholder Stock Approval', vehicle: 'Placeholder #PLH-041', submittedBy: 'Jordan Davis (Manager)', time: '7:48 AM', priority: 'Medium' },
  { id: 'a3', type: 'Price Override Approval', vehicle: '2023 Tesla Model 3 LR · Stock M48302', submittedBy: 'Ben Wheeler (Sales)', time: '7:31 AM', priority: 'High' },
  { id: 'a4', type: 'Trade-In Valuation Sign-off', vehicle: '2019 Honda CR-V · Stock Fresh Trade', submittedBy: 'Lisa Martinez (Sales)', time: '6:55 AM', priority: 'Medium' },
]

function StockPill({ stock, onSelect }: { stock: string; onSelect: (s: string) => void }) {
  return (
    <button onClick={() => onSelect(stock)} className="font-mono text-[11px] font-bold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-1.5 py-0.5 rounded transition-colors">
      {stock}
    </button>
  )
}

export default function ControllerDashboard({ onVehicleSelect }: { onVehicleSelect: (s: string) => void }) {
  const [filterType, setFilterType] = useState<ExceptionType | 'All'>('All')
  const [resolvedIds, setResolvedIds] = useState<Set<string>>(new Set())
  const [approvedIds, setApprovedIds] = useState<Set<string>>(new Set())

  const filtered = exceptions.filter(e =>
    !resolvedIds.has(e.id) &&
    (filterType === 'All' || e.type === filterType)
  )

  const openCount = exceptions.filter(e => !resolvedIds.has(e.id) && e.status === 'Open').length
  const pendingAudit = auditQueue.filter(a => !approvedIds.has(a.id)).length

  return (
    <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5" style={{ scrollbarWidth: 'thin' }}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-[22px] font-bold text-slate-900 tracking-tight">Controller Dashboard</h1>
          <p className="text-[13px] text-slate-500 mt-0.5">DMS sync · Inventory audit · Exception management</p>
        </div>
        <div className="flex items-center gap-3">
          {/* KPI strip */}
          {[
            { label: 'Open Exceptions', v: openCount.toString(), c: 'text-red-600' },
            { label: 'Pending Audit', v: pendingAudit.toString(), c: 'text-amber-600' },
            { label: 'Resolved Today', v: resolvedIds.size.toString(), c: 'text-emerald-600' },
            { label: 'Last Recon', v: '7:08 AM', c: 'text-slate-900' },
          ].map(k => (
            <div key={k.label} className="bg-white rounded-xl border border-slate-200 px-4 py-3 text-center min-w-[100px]">
              <div className={`text-[20px] font-bold ${k.c}`}>{k.v}</div>
              <div className="text-[10px] text-slate-400 mt-0.5">{k.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Reconciliation status banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-100 flex items-center justify-center flex-shrink-0">
              <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" stroke="#16A34A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </div>
            <div>
              <div className="text-[14px] font-bold text-slate-900">Morning Sync Complete</div>
              <div className="text-[12px] text-slate-500 mt-0.5">Ran at 7:08 AM · 1,247 vehicles processed · 23 exceptions found · 1m 42s runtime</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-4 pr-4 border-r border-slate-100">
              {[
                { label: 'In Tekion', v: '1,247', ok: true },
                { label: 'On Lot (Keyper)', v: '1,189', ok: false },
                { label: 'With RecovR', v: '1,162', ok: false },
                { label: 'Discrepancy', v: '85', ok: false, critical: true },
              ].map(s => (
                <div key={s.label} className="text-center">
                  <div className={`text-[16px] font-bold tabular-nums ${s.critical ? 'text-red-600' : s.ok ? 'text-emerald-600' : 'text-slate-800'}`}>{s.v}</div>
                  <div className="text-[10px] text-slate-400">{s.label}</div>
                </div>
              ))}
            </div>
            <button className="text-[12px] font-bold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-4 py-2 rounded-xl transition-colors">
              Re-run Sync
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-5" style={{ gridTemplateColumns: '1fr 340px' }}>
        {/* VIN Exceptions Table */}
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <h3 className="text-[14px] font-bold text-slate-900">VIN Exceptions</h3>
              <span className="text-[11px] font-bold text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">{filtered.length} open</span>
            </div>
            <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
              {(['All', 'Missing from DMS', 'Not Found on Lot', 'Duplicate VIN', 'Price Discrepancy', 'Missing Title'] as (ExceptionType | 'All')[]).map(t => (
                <button key={t} onClick={() => setFilterType(t)}
                  className={`text-[10px] font-semibold px-2 py-1 rounded-md transition-all ${filterType === t ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
                  {t === 'All' ? 'All' : t.split(' ').slice(0, 2).join(' ')}
                </button>
              ))}
            </div>
          </div>

          <table className="w-full text-[12px]">
            <thead>
              <tr className="bg-slate-50/70 border-b border-slate-100">
                {['Exception Type', 'Vehicle', 'VIN', 'Days', 'Assigned', 'Status', ''].map(h => (
                  <th key={h} className="text-left text-[10px] font-bold text-slate-400 uppercase tracking-wider px-4 py-2.5">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(ex => {
                const et = exTypeMeta[ex.type]
                const es = exStatusMeta[ex.status]
                return (
                  <tr key={ex.id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors group">
                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${et.bg} ${et.text}`}>{ex.type}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-900">{ex.make} {ex.model}</div>
                      <StockPill stock={ex.stock} onSelect={onVehicleSelect} />
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-[11px] text-slate-400">{ex.vin}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-bold tabular-nums ${ex.days >= 5 ? 'text-red-600' : ex.days >= 2 ? 'text-amber-600' : 'text-slate-700'}`}>{ex.days}d</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-semibold ${ex.assignedTo === 'Unassigned' ? 'text-red-500' : 'text-slate-700'}`}>{ex.assignedTo}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${es.bg} ${es.text}`}>{ex.status}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button onClick={() => setResolvedIds(r => new Set(r).add(ex.id))}
                          className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded transition-colors hover:bg-emerald-100">
                          Resolve
                        </button>
                        <button className="text-[10px] font-bold text-slate-500 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded hover:bg-slate-100">
                          Review
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-400 text-[13px]">All exceptions resolved 🎉</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Audit Queue */}
        <div className="space-y-4">
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <h3 className="text-[14px] font-bold text-slate-900">Audit Queue</h3>
                {pendingAudit > 0 && <span className="text-[10px] font-bold text-white bg-amber-500 px-1.5 py-0.5 rounded-full">{pendingAudit}</span>}
              </div>
              <span className="text-[11px] text-slate-400">Requires your approval</span>
            </div>
            <div className="divide-y divide-slate-50">
              {auditQueue.filter(a => !approvedIds.has(a.id)).map(item => (
                <div key={item.id} className="px-5 py-4 hover:bg-slate-50 transition-colors">
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${item.priority === 'High' ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'}`}>{item.priority}</span>
                    <span className="text-[10px] text-slate-400">{item.time}</span>
                  </div>
                  <div className="text-[13px] font-bold text-slate-900 mb-0.5">{item.type}</div>
                  <div className="text-[11px] text-slate-500 mb-0.5">{item.vehicle}</div>
                  <div className="text-[11px] text-slate-400 mb-3">Submitted by {item.submittedBy}</div>
                  <div className="flex gap-2">
                    <button onClick={() => setApprovedIds(a => new Set(a).add(item.id))}
                      className="flex-1 h-8 bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold rounded-lg transition-colors">
                      Approve
                    </button>
                    <button className="flex-1 h-8 bg-slate-50 hover:bg-slate-100 text-slate-600 text-[11px] font-semibold border border-slate-200 rounded-lg transition-colors">
                      Hold
                    </button>
                    <button onClick={() => setApprovedIds(a => new Set(a).add(item.id))}
                      className="h-8 px-3 bg-red-50 hover:bg-red-100 text-red-600 text-[11px] font-semibold border border-red-200 rounded-lg transition-colors">
                      Reject
                    </button>
                  </div>
                </div>
              ))}
              {auditQueue.filter(a => !approvedIds.has(a.id)).length === 0 && (
                <div className="px-5 py-6 text-center text-slate-400 text-[13px]">Audit queue clear ✓</div>
              )}
            </div>
          </div>

          {/* Inventory counts */}
          <div className="bg-white rounded-2xl border border-slate-200 p-4">
            <div className="text-[12px] font-bold text-slate-700 uppercase tracking-wider mb-3">Inventory Summary</div>
            <div className="space-y-2">
              {[
                { label: 'Total in DMS (Tekion)', v: '1,247', c: 'text-slate-900' },
                { label: 'Total in Keyper', v: '1,189', c: 'text-slate-800' },
                { label: 'Unaccounted (Keyper)', v: '58', c: 'text-amber-600' },
                { label: 'With GPS (RecovR)', v: '1,162', c: 'text-slate-800' },
                { label: 'Missing GPS', v: '85', c: 'text-red-500' },
                { label: 'Placeholder Stocks', v: '4', c: 'text-amber-600' },
                { label: 'Sold Today (not closed)', v: '2', c: 'text-red-500' },
              ].map(s => (
                <div key={s.label} className="flex items-center justify-between py-1 border-b border-slate-50 last:border-0">
                  <span className="text-[11px] text-slate-500">{s.label}</span>
                  <span className={`text-[13px] font-bold tabular-nums ${s.c}`}>{s.v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
