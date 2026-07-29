import { useState } from 'react'

type TradeStatus = 'Pending Pickup' | 'Awaiting Driver' | 'In Transit' | 'Arrived' | 'Accepted'

const tradeMeta: Record<TradeStatus, { bg: string; text: string; dot: string }> = {
  'Pending Pickup': { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-400' },
  'Awaiting Driver': { bg: 'bg-red-50', text: 'text-red-600', dot: 'bg-red-500' },
  'In Transit': { bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-400' },
  Arrived: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-400' },
  Accepted: { bg: 'bg-violet-50', text: 'text-violet-700', dot: 'bg-violet-400' },
}

const dealerTrades = [
  { id: 'dt1', status: 'Awaiting Driver' as TradeStatus, stock: 'H72840', vehicle: '2022 Honda Civic Sport Hatch', vin: '2HGFA1F54AH302018', from: 'Central Honda', to: 'Sunrise Toyota', driver: null, eta: 'ASAP', urgent: true },
  { id: 'dt2', status: 'Pending Pickup' as TradeStatus, stock: 'F38102', vehicle: '2021 Ford F-150 XLT 4x4', vin: '1FTEW1E53JKD03928', from: 'Sunrise Toyota', to: 'Metro Ford', driver: 'Marcus Torres', eta: 'By 11 AM', urgent: false },
  { id: 'dt3', status: 'In Transit' as TradeStatus, stock: 'G10923', vehicle: '2023 Lexus ES 350 F Sport', vin: 'JTHBF30G175031729', from: 'Sunrise Toyota', to: 'Prestige Lexus', driver: 'David Okafor', eta: '~45 min', urgent: false },
  { id: 'dt4', status: 'Accepted' as TradeStatus, stock: 'N20381', vehicle: '2023 Audi A6 Premium Plus', vin: 'WAUYGAFC5CN004752', from: 'Coastal Audi', to: 'Sunrise Toyota', driver: 'K. Williams', eta: '~2 hrs', urgent: false },
  { id: 'dt5', status: 'Arrived' as TradeStatus, stock: 'B93021', vehicle: '2022 Volkswagen Jetta SE', vin: '3VWFE21C04M000001', from: 'Valley VW', to: 'Sunrise Toyota', driver: 'S. Park', eta: 'Arrived 7:41 AM', urgent: false },
]

const incomingVehicles = [
  { stock: 'TBD', vehicle: '2024 Toyota Camry XSE V6', qty: 3, from: 'Southeast Toyota', eta: 'Today 10:30 AM', status: 'On Transport' },
  { stock: 'TBD', vehicle: '2024 Honda CR-V Sport Touring', qty: 2, from: 'American Honda', eta: 'Today 2:00 PM', status: 'On Transport' },
  { stock: 'M48302', vehicle: '2023 Tesla Model 3 Long Range', qty: 1, from: 'Tesla Direct', eta: 'Arrived — Staging', status: 'Awaiting DMS Entry' },
  { stock: 'TBD', vehicle: '2024 Ford Bronco Sport Big Bend', qty: 1, from: 'Ford Motor Co.', eta: 'Tomorrow AM', status: 'Scheduled' },
]

const movements = [
  { id: 'm1', vehicle: '2023 Honda Accord EX-L', stock: 'A48291', from: 'Row 4, Space 12', to: 'Showroom Bay 2', assigned: 'S. Park', priority: 'High' },
  { id: 'm2', vehicle: '2022 Lexus RX 350', stock: 'L83042', from: 'Recon Bay 3', to: 'Lot Row 2, Space 8', assigned: 'M. Torres', priority: 'Medium' },
  { id: 'm3', vehicle: '2021 Toyota Tacoma TRD', stock: 'T38291', from: 'Incoming Bay', to: 'Lot Row 7, Space 4', assigned: 'Unassigned', priority: 'High' },
  { id: 'm4', vehicle: '2023 Chevy Silverado 1500', stock: 'C19302', from: 'Lot Row 1, Space 3', to: 'Detail Bay 1', assigned: 'D. Okafor', priority: 'Low' },
]

function StockPill({ stock, onSelect }: { stock: string; onSelect: (s: string) => void }) {
  if (stock === 'TBD') return <span className="font-mono text-[11px] font-bold text-slate-400">TBD</span>
  return (
    <button onClick={() => onSelect(stock)} className="font-mono text-[11px] font-bold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-1.5 py-0.5 rounded transition-colors">
      {stock}
    </button>
  )
}

export default function TowerManagerDashboard({ onVehicleSelect }: { onVehicleSelect: (s: string) => void }) {
  const [filter, setFilter] = useState<TradeStatus | 'All'>('All')

  const filtered = filter === 'All' ? dealerTrades : dealerTrades.filter(t => t.status === filter)

  return (
    <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5" style={{ scrollbarWidth: 'thin' }}>
      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-[22px] font-bold text-slate-900 tracking-tight">Tower Overview</h1>
          <p className="text-[13px] text-slate-500 mt-0.5">Vehicle movement · Dealer trades · Incoming inventory</p>
        </div>
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: 'Trades Pending', v: '4', c: 'text-amber-600' },
            { label: 'In Transit', v: '1', c: 'text-blue-600' },
            { label: 'Incoming Today', v: '6', c: 'text-emerald-600' },
            { label: 'Movements Queued', v: '4', c: 'text-slate-900' },
          ].map(k => (
            <div key={k.label} className="bg-white rounded-xl border border-slate-200 px-4 py-3 text-center">
              <div className={`text-[22px] font-bold ${k.c}`}>{k.v}</div>
              <div className="text-[10px] text-slate-400 mt-0.5">{k.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-5" style={{ gridTemplateColumns: '1fr 340px' }}>
        {/* LEFT — Dealer Trades */}
        <div className="space-y-4">
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100">
              <div>
                <h3 className="text-[14px] font-bold text-slate-900">Dealer Trades</h3>
                <p className="text-[11px] text-slate-400 mt-0.5">{dealerTrades.length} active trades today</p>
              </div>
              <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
                {(['All', 'Awaiting Driver', 'Pending Pickup', 'In Transit', 'Accepted', 'Arrived'] as (TradeStatus | 'All')[]).map(s => (
                  <button key={s} onClick={() => setFilter(s)}
                    className={`text-[10px] font-semibold px-2 py-1 rounded-md transition-all ${filter === s ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
                    {s}
                  </button>
                ))}
              </div>
            </div>

            <div className="divide-y divide-slate-50">
              {filtered.map(trade => {
                const tm = tradeMeta[trade.status]
                return (
                  <div key={trade.id} className={`px-5 py-4 hover:bg-slate-50 transition-colors group ${trade.urgent ? 'border-l-2 border-red-400' : ''}`}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className={`inline-flex items-center gap-1.5 text-[11px] font-bold px-2 py-0.5 rounded-full ${tm.bg} ${tm.text}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${tm.dot}`} />
                            {trade.status}
                          </span>
                          {trade.urgent && <span className="text-[10px] font-bold text-red-500 animate-pulse">Urgent</span>}
                          <StockPill stock={trade.stock} onSelect={onVehicleSelect} />
                        </div>
                        <div className="text-[14px] font-bold text-slate-900 mb-0.5">{trade.vehicle}</div>
                        <div className="text-[11px] font-mono text-slate-400 mb-2">{trade.vin}</div>
                        <div className="flex items-center gap-4 text-[11px] text-slate-500">
                          <span className="flex items-center gap-1">
                            <span className="font-semibold text-slate-700">From:</span> {trade.from}
                          </span>
                          <span>→</span>
                          <span className="flex items-center gap-1">
                            <span className="font-semibold text-slate-700">To:</span> {trade.to}
                          </span>
                        </div>
                      </div>
                      <div className="flex-shrink-0 text-right">
                        <div className="text-[11px] text-slate-400 mb-0.5">Driver</div>
                        <div className={`text-[12px] font-bold ${trade.driver ? 'text-slate-800' : 'text-red-500'}`}>
                          {trade.driver ?? 'Unassigned'}
                        </div>
                        <div className="text-[11px] font-semibold text-amber-600 mt-1">{trade.eta}</div>
                      </div>
                    </div>
                    <div className="flex gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                      {!trade.driver && (
                        <button className="text-[11px] font-bold text-white bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded-lg transition-colors">
                          Assign Driver
                        </button>
                      )}
                      <button className="text-[11px] font-bold text-slate-600 hover:text-slate-800 bg-slate-50 hover:bg-slate-100 border border-slate-200 px-3 py-1 rounded-lg transition-colors">
                        View Details
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Vehicle Movement */}
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100">
              <h3 className="text-[14px] font-bold text-slate-900">Movement Queue</h3>
              <span className="text-[11px] font-semibold text-slate-500">{movements.length} pending</span>
            </div>
            <div className="divide-y divide-slate-50">
              {movements.map(m => {
                const unassigned = m.assigned === 'Unassigned'
                return (
                  <div key={m.id} className="flex items-center gap-4 px-5 py-3 hover:bg-slate-50 transition-colors group">
                    <div className={`w-2 h-2 rounded-full flex-shrink-0 ${m.priority === 'High' ? 'bg-orange-500' : m.priority === 'Low' ? 'bg-slate-400' : 'bg-amber-400'}`} />
                    <div className="flex-1 min-w-0">
                      <div className="text-[13px] font-bold text-slate-900 truncate">{m.vehicle}</div>
                      <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
                        <StockPill stock={m.stock} onSelect={onVehicleSelect} />
                        <span className="font-semibold text-slate-600">{m.from}</span>
                        <span>→</span>
                        <span className="font-semibold text-slate-600">{m.to}</span>
                      </div>
                    </div>
                    <div className={`text-[12px] font-bold ${unassigned ? 'text-red-500' : 'text-slate-700'} flex-shrink-0`}>{m.assigned}</div>
                    <button className="text-[11px] font-bold text-blue-600 hover:text-blue-700 bg-blue-50 border border-blue-200 px-2.5 py-1 rounded-lg transition-colors opacity-0 group-hover:opacity-100">
                      {unassigned ? 'Assign' : 'Start'}
                    </button>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* RIGHT — Incoming + Staging */}
        <div className="space-y-4">
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100">
              <h3 className="text-[14px] font-bold text-slate-900">Incoming Inventory</h3>
              <span className="text-[10px] font-semibold text-blue-600 bg-blue-50 border border-blue-100 px-2 py-0.5 rounded-full">{incomingVehicles.reduce((a, v) => a + v.qty, 0)} vehicles</span>
            </div>
            <div className="divide-y divide-slate-50">
              {incomingVehicles.map((v, i) => (
                <div key={i} className="px-5 py-3.5 hover:bg-slate-50 transition-colors">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div>
                      <div className="text-[13px] font-bold text-slate-900">{v.vehicle}</div>
                      <div className="text-[11px] text-slate-400">From: {v.from} · Qty: {v.qty}</div>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <div className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        v.status === 'Awaiting DMS Entry' ? 'bg-amber-50 text-amber-700' : v.status === 'On Transport' ? 'bg-blue-50 text-blue-700' : 'bg-slate-100 text-slate-600'
                      }`}>{v.status}</div>
                    </div>
                  </div>
                  <div className="text-[11px] font-semibold text-slate-600">{v.eta}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Lot Staffing */}
          <div className="bg-white rounded-2xl border border-slate-200 p-4">
            <div className="text-[12px] font-bold text-slate-700 uppercase tracking-wider mb-3">Lot Staffing</div>
            <div className="space-y-2">
              {[
                { name: 'Marcus Torres', status: 'On Trade Run', dot: 'bg-blue-400' },
                { name: 'Keisha Williams', status: 'Available', dot: 'bg-emerald-400' },
                { name: 'David Okafor', status: 'Trade Run ETA 45m', dot: 'bg-amber-400' },
                { name: 'Sara Park', status: 'Available', dot: 'bg-emerald-400' },
                { name: 'T. Mabunda', status: 'Lunch · Back 12:30', dot: 'bg-slate-300' },
              ].map(m => (
                <div key={m.name} className="flex items-center gap-2.5 py-1.5">
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${m.dot}`} />
                  <span className="text-[12px] font-semibold text-slate-800 flex-1">{m.name}</span>
                  <span className="text-[11px] text-slate-400">{m.status}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Quick stats */}
          <div className="bg-white rounded-2xl border border-slate-200 p-4">
            <div className="text-[12px] font-bold text-slate-700 uppercase tracking-wider mb-3">Today's Summary</div>
            <div className="space-y-2">
              {[
                { label: 'Trades Completed', v: '5', c: 'text-emerald-600' },
                { label: 'Vehicles Received', v: '3', c: 'text-blue-600' },
                { label: 'Vehicles Staged', v: '8', c: 'text-slate-900' },
                { label: 'Awaiting Driver', v: '1', c: 'text-red-500' },
              ].map(s => (
                <div key={s.label} className="flex items-center justify-between py-1 border-b border-slate-50 last:border-0">
                  <span className="text-[12px] text-slate-500">{s.label}</span>
                  <span className={`text-[14px] font-bold ${s.c}`}>{s.v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
