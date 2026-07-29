import { useState, useEffect, useRef, useMemo } from 'react'

type StageId = 'incoming' | 'inspection' | 'fuel' | 'photos' | 'ready' | 'showroom' | 'dealer-trade'

interface StagedVehicle {
  id: string
  stock: string
  year: number
  make: string
  model: string
  color: string
  stage: StageId
  priority: 'urgent' | 'normal'
  timeInStage: string
  assignedTo?: string
  note?: string
}

const STAGES: { id: StageId; label: string; color: string; capacity: number }[] = [
  { id: 'incoming',     label: 'Incoming',     color: 'bg-blue-500',    capacity: 10 },
  { id: 'inspection',   label: 'Inspection',   color: 'bg-violet-500',  capacity: 8  },
  { id: 'fuel',         label: 'Fuel',         color: 'bg-yellow-500',  capacity: 6  },
  { id: 'photos',       label: 'Photos',       color: 'bg-pink-500',    capacity: 8  },
  { id: 'ready',        label: 'Ready',        color: 'bg-emerald-500', capacity: 20 },
  { id: 'showroom',     label: 'Showroom',     color: 'bg-purple-500',  capacity: 6  },
  { id: 'dealer-trade', label: 'Dealer Trade', color: 'bg-orange-500',  capacity: 8  },
]

const VEHICLES: StagedVehicle[] = [
  { id: 'K28391', stock: 'K28391', year: 2024, make: 'Toyota',    model: 'Camry',      color: 'Midnight Black',    stage: 'incoming',     priority: 'normal', timeInStage: '22m',    note: 'From Axis Transport' },
  { id: 'K28392', stock: 'K28392', year: 2023, make: 'Honda',     model: 'Accord',     color: 'Lunar Silver',      stage: 'incoming',     priority: 'normal', timeInStage: '8m' },
  { id: 'K28393', stock: 'K28393', year: 2024, make: 'Kia',       model: 'Telluride',  color: 'Gravity Gray',      stage: 'incoming',     priority: 'urgent', timeInStage: '1h 14m', note: 'Delayed delivery — check notes' },
  { id: 'A48291', stock: 'A48291', year: 2023, make: 'Honda',     model: 'Accord',     color: 'Sonic Gray Pearl',  stage: 'inspection',   priority: 'normal', timeInStage: '34m',    assignedTo: 'Marcus Torres' },
  { id: 'E51390', stock: 'E51390', year: 2022, make: 'BMW',       model: 'X5',         color: 'Alpine White',      stage: 'inspection',   priority: 'normal', timeInStage: '1h 2m',  assignedTo: 'K. Williams' },
  { id: 'F29917', stock: 'F29917', year: 2022, make: 'Chevrolet', model: 'Silverado',  color: 'Black',             stage: 'fuel',         priority: 'normal', timeInStage: '18m',    assignedTo: 'Marcus Torres' },
  { id: 'C84711', stock: 'C84711', year: 2022, make: 'Ford',      model: 'F-150',      color: 'Oxford White',      stage: 'fuel',         priority: 'normal', timeInStage: '45m',    assignedTo: 'Marcus Torres' },
  { id: 'D72044', stock: 'D72044', year: 2024, make: 'Kia',       model: 'Telluride',  color: 'Everest White',     stage: 'photos',       priority: 'normal', timeInStage: '1h 20m', assignedTo: 'K. Williams' },
  { id: 'H64509', stock: 'H64509', year: 2023, make: 'Mazda',     model: 'CX-5',       color: 'Platinum Quartz',   stage: 'photos',       priority: 'normal', timeInStage: '2h 5m',  assignedTo: 'K. Williams' },
  { id: 'M29481', stock: 'M29481', year: 2022, make: 'Ford',      model: 'Explorer',   color: 'Carbonized Gray',   stage: 'photos',       priority: 'urgent', timeInStage: '3h',     assignedTo: 'Unassigned',  note: 'Overdue — reassign' },
  { id: 'G11203', stock: 'G11203', year: 2024, make: 'Hyundai',   model: 'Tucson',     color: 'Shimmering Silver', stage: 'ready',        priority: 'normal', timeInStage: '2h 14m' },
  { id: 'B93021', stock: 'B93021', year: 2024, make: 'Toyota',    model: 'Camry',      color: 'Midnight Black',    stage: 'ready',        priority: 'normal', timeInStage: '47m' },
  { id: 'P28100', stock: 'P28100', year: 2023, make: 'Honda',     model: 'Accord',     color: 'Lunar Silver',      stage: 'ready',        priority: 'normal', timeInStage: '4h 30m' },
  { id: 'E51389', stock: 'E51389', year: 2023, make: 'BMW',       model: '3 Series',   color: 'Black Sapphire',    stage: 'ready',        priority: 'normal', timeInStage: '1h 8m' },
  { id: 'E51388', stock: 'E51388', year: 2023, make: 'BMW',       model: '5 Series',   color: 'Mineral White',     stage: 'showroom',     priority: 'normal', timeInStage: '3h 20m', note: 'Sales request' },
  { id: 'A48290', stock: 'A48290', year: 2022, make: 'Honda',     model: 'Civic',      color: 'Rallye Red',        stage: 'showroom',     priority: 'normal', timeInStage: '1h 45m' },
  { id: 'H72840', stock: 'H72840', year: 2023, make: 'Subaru',    model: 'Outback',    color: 'Crystal White',     stage: 'dealer-trade', priority: 'urgent', timeInStage: '28m',    assignedTo: 'Jordan Davis', note: 'Awaiting pickup — ASAP' },
  { id: 'G19283', stock: 'G19283', year: 2022, make: 'Toyota',    model: 'RAV4',       color: 'Magnetic Gray',     stage: 'dealer-trade', priority: 'urgent', timeInStage: '28m',    assignedTo: 'Jordan Davis' },
]

function CapacityBar({ count, capacity, colorClass }: { count: number; capacity: number; colorClass: string }) {
  const pct = Math.min((count / capacity) * 100, 100)
  const barColor = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-500' : colorClass
  return (
    <div className="h-1 bg-slate-200 rounded-full mt-1.5 overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-300 ${barColor}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

interface VehicleCardProps {
  vehicle: StagedVehicle
  moveMenuOpen: string | null
  setMoveMenuOpen: (id: string | null) => void
  onMove: (vehicleId: string, stage: StageId) => void
}

function VehicleCard({ vehicle, moveMenuOpen, setMoveMenuOpen, onMove }: VehicleCardProps) {
  const [hovered, setHovered] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const isMenuOpen = moveMenuOpen === vehicle.id

  useEffect(() => {
    if (!isMenuOpen) return
    function handleOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMoveMenuOpen(null)
      }
    }
    document.addEventListener('mousedown', handleOutside)
    return () => document.removeEventListener('mousedown', handleOutside)
  }, [isMenuOpen, setMoveMenuOpen])

  const isUnassigned = !vehicle.assignedTo || vehicle.assignedTo === 'Unassigned'

  return (
    <div
      className={`relative bg-white rounded-xl border border-slate-200 p-3 shadow-sm cursor-default select-none transition-all duration-150 ${hovered ? 'shadow-md -translate-y-0.5' : ''}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => { setHovered(false) }}
    >
      {/* Row 1: stock + time */}
      <div className="flex items-center gap-1 mb-0.5">
        {vehicle.priority === 'urgent' && (
          <span className="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0" />
        )}
        <span className="font-mono text-[10px] text-blue-600 tracking-tight">{vehicle.stock}</span>
        <span className="ml-auto text-[9px] text-slate-400">{vehicle.timeInStage}</span>
      </div>

      {/* Row 2: year make model */}
      <div className="text-[12px] font-bold text-slate-900 leading-tight">
        {vehicle.year} {vehicle.make} {vehicle.model}
      </div>

      {/* Row 3: color */}
      <div className="text-[10px] text-slate-500 mt-0.5">{vehicle.color}</div>

      {/* Row 4: assigned */}
      <div className="mt-1.5">
        {isUnassigned ? (
          <span className="inline-flex items-center gap-1 text-[10px] text-amber-600 border border-dashed border-amber-400 rounded px-1.5 py-0.5">
            Unassigned
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-[10px] text-slate-600 bg-slate-100 rounded px-1.5 py-0.5">
            <svg width="8" height="8" viewBox="0 0 16 16" fill="currentColor">
              <circle cx="8" cy="5" r="3.5" />
              <path d="M1 14c0-3.866 3.134-7 7-7s7 3.134 7 7" />
            </svg>
            {vehicle.assignedTo}
          </span>
        )}
      </div>

      {/* Note */}
      {vehicle.note && (
        <div className="mt-1 text-[9px] text-amber-700 bg-amber-50 rounded px-1.5 py-0.5 leading-tight">
          {vehicle.note}
        </div>
      )}

      {/* Move button (hover) */}
      {hovered && (
        <div className="mt-2 relative" ref={menuRef}>
          <button
            className="text-[10px] text-blue-600 font-bold hover:text-blue-700"
            onClick={(e) => {
              e.stopPropagation()
              setMoveMenuOpen(isMenuOpen ? null : vehicle.id)
            }}
          >
            Move to next stage →
          </button>

          {isMenuOpen && (
            <div className="absolute left-0 top-full mt-1 z-50 bg-white border border-slate-200 rounded-lg shadow-lg py-1 w-40">
              {STAGES.map((s) => (
                <button
                  key={s.id}
                  className="w-full text-left text-[11px] text-slate-700 hover:bg-slate-50 px-3 py-1.5 flex items-center gap-2"
                  onClick={(e) => {
                    e.stopPropagation()
                    onMove(vehicle.id, s.id)
                  }}
                >
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${s.color}`} />
                  {s.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

interface ColumnProps {
  stage: typeof STAGES[number]
  vehicles: StagedVehicle[]
  moveMenuOpen: string | null
  setMoveMenuOpen: (id: string | null) => void
  onMove: (vehicleId: string, stage: StageId) => void
}

function Column({ stage, vehicles, moveMenuOpen, setMoveMenuOpen, onMove }: ColumnProps) {
  return (
    <div className="w-52 flex-shrink-0 flex flex-col h-full">
      {/* Column header */}
      <div className="bg-white rounded-xl border border-slate-200 px-3 py-2.5 mb-2 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full flex-shrink-0 ${stage.color}`} />
            <span className="text-[12px] font-semibold text-slate-800">{stage.label}</span>
          </div>
          <span className="text-[10px] font-bold text-slate-500 bg-slate-100 rounded-full px-1.5 py-0.5">
            {vehicles.length}
          </span>
        </div>
        <CapacityBar count={vehicles.length} capacity={stage.capacity} colorClass={stage.color} />
      </div>

      {/* Cards */}
      <div
        className="flex-1 overflow-y-auto space-y-2 pb-2"
        style={{ scrollbarWidth: 'none' }}
      >
        {vehicles.length === 0 && (
          <div className="text-[10px] text-slate-400 text-center mt-4">No vehicles</div>
        )}
        {vehicles.map((v) => (
          <VehicleCard
            key={v.id}
            vehicle={v}
            moveMenuOpen={moveMenuOpen}
            setMoveMenuOpen={setMoveMenuOpen}
            onMove={onMove}
          />
        ))}
      </div>
    </div>
  )
}

export default function Staging(): JSX.Element {
  const [stageOverrides, setStageOverrides] = useState<Record<string, StageId>>({})
  const [moveMenuOpen, setMoveMenuOpen] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  function handleMove(vehicleId: string, stage: StageId) {
    setStageOverrides((prev) => ({ ...prev, [vehicleId]: stage }))
    setMoveMenuOpen(null)
  }

  const filteredVehicles = useMemo(() => {
    const q = search.trim().toLowerCase()
    return VEHICLES.filter((v) => {
      if (!q) return true
      return (
        v.stock.toLowerCase().includes(q) ||
        v.make.toLowerCase().includes(q) ||
        v.model.toLowerCase().includes(q)
      )
    })
  }, [search])

  const vehiclesByStage = useMemo(() => {
    const map: Record<StageId, StagedVehicle[]> = {
      incoming: [], inspection: [], fuel: [], photos: [], ready: [], showroom: [], 'dealer-trade': [],
    }
    for (const v of filteredVehicles) {
      const effectiveStage = stageOverrides[v.id] ?? v.stage
      map[effectiveStage].push(v)
    }
    return map
  }, [filteredVehicles, stageOverrides])

  return (
    <div className="flex flex-col h-screen bg-slate-100">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-5 py-3 flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-[16px] font-bold text-slate-900 leading-tight">Staging Board</h1>
          <p className="text-[11px] text-slate-500">Live lot pipeline</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative">
            <svg
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"
              width="13"
              height="13"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="9" cy="9" r="6" />
              <path d="M15 15l3 3" strokeLinecap="round" />
            </svg>
            <input
              type="text"
              placeholder="Search stock, make, model…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-7 pr-3 py-1.5 text-[12px] border border-slate-200 rounded-lg bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 w-52 text-slate-700 placeholder-slate-400"
            />
          </div>
          {/* Date */}
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5">
            <svg width="12" height="12" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="4" width="14" height="14" rx="2" />
              <path d="M3 8h14M7 2v4M13 2v4" strokeLinecap="round" />
            </svg>
            Today · Mon Jul 28
          </div>
        </div>
      </div>

      {/* Kanban area */}
      <div className="flex-1 flex overflow-x-auto px-4 py-4 gap-3 min-h-0">
        {STAGES.map((stage) => (
          <Column
            key={stage.id}
            stage={stage}
            vehicles={vehiclesByStage[stage.id]}
            moveMenuOpen={moveMenuOpen}
            setMoveMenuOpen={setMoveMenuOpen}
            onMove={handleMove}
          />
        ))}
      </div>
    </div>
  )
}
