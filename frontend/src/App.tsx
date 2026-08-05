import { useState, useCallback, useEffect, useRef } from 'react'
import VehicleDetailPage from './VehicleDetail'
import Dashboard from './dashboards/Dashboard'
import VehiclesList from './dashboards/VehiclesList'
import Tasks from './dashboards/Tasks'
import InventorySync from './dashboards/InventorySync'
import Profile from './dashboards/Profile'
import { getDashboard } from './api/dashboard'
import { useApi } from './api/useApi'

// ─── Types ────────────────────────────────────────────────────────────────────

type Role = 'Lot Staff' | 'Lot Manager' | 'Tower Manager' | 'Controller' | 'Sales Manager' | 'Recon Manager' | 'Service Advisor' | 'Detail Team'

interface RoleConfig {
  initials: string
  color: string
  name: string
  title: string
  navGroup: string
}

// ─── Role config ──────────────────────────────────────────────────────────────

const roleConfig: Record<Role, RoleConfig> = {
  'Lot Staff': { initials: 'MT', color: '#2563EB', name: 'Marcus Torres', title: 'Lot Attendant', navGroup: 'core' },
  'Lot Manager': { initials: 'JD', color: '#0891B2', name: 'Jordan Davis', title: 'Lot Manager', navGroup: 'core' },
  'Tower Manager': { initials: 'RP', color: '#7C3AED', name: 'Rosa Pereira', title: 'Tower Manager', navGroup: 'core' },
  'Controller': { initials: 'SK', color: '#DC2626', name: 'Sarah Kim', title: 'Controller', navGroup: 'core' },
  'Sales Manager': { initials: 'BW', color: '#059669', name: 'Ben Wheeler', title: 'Sales Manager', navGroup: 'core' },
  'Recon Manager': { initials: 'AH', color: '#D97706', name: 'Alex Huang', title: 'Recon Manager', navGroup: 'core' },
  'Service Advisor': { initials: 'LM', color: '#0891B2', name: 'Lisa Martinez', title: 'Service Advisor', navGroup: 'core' },
  'Detail Team': { initials: 'DT', color: '#64748B', name: 'Detail Team', title: 'Detail Attendant', navGroup: 'core' },
}

const roleOrder: Role[] = ['Lot Staff', 'Lot Manager', 'Tower Manager', 'Controller', 'Sales Manager', 'Recon Manager', 'Service Advisor', 'Detail Team']

// ─── Nav items per role group ─────────────────────────────────────────────────

interface NavItem { id: string; label: string; icon: JSX.Element }

function svgIcon(d: string, d2?: string) {
  return (
    <svg width="15" height="15" fill="none" viewBox="0 0 24 24">
      <path d={d} stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
      {d2 && <path d={d2} stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />}
    </svg>
  )
}

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return iso
  const minutes = Math.round((Date.now() - then) / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} hr ago`
  const days = Math.round(hours / 24)
  return `${days} day${days === 1 ? '' : 's'} ago`
}

// Sprint 3.8 alignment: one nav for every role. Lot Staff is the only
// primary user; Tower/Sales/Service/Controller are contributors who
// feed information to lot staff rather than getting a dedicated
// workspace, so navigation no longer branches per role.
const NAV: Record<string, NavItem[]> = {
  core: [
    { id: 'dashboard',     label: 'Dashboard',      icon: svgIcon('M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z') },
    { id: 'vehicles',      label: 'Vehicles',        icon: svgIcon('M5 17H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h13l4 4v4a2 2 0 0 1-2 2h-2', 'M5 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0zM15 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0z') },
    { id: 'tasks',         label: 'Tasks',           icon: svgIcon('M9 11l3 3L22 4', 'M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11') },
    { id: 'inventory-sync',label: 'Inventory Sync',  icon: svgIcon('M23 4v6h-6M1 20v-6h6', 'M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15') },
  ],
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function Sidebar({ role, activeNav, onNav }: { role: Role; activeNav: string; onNav: (id: string) => void; }) {
  const cfg = roleConfig[role]
  const items = NAV[cfg.navGroup]

  return (
    <aside className="w-52 flex-shrink-0 flex flex-col h-screen" style={{ backgroundColor: '#0B1629' }}>
      {/* Logo */}
      <div className="px-4 pt-5 pb-4 border-b border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-blue-600 flex items-center justify-center flex-shrink-0">
            <svg width="13" height="13" fill="none" viewBox="0 0 24 24">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <div className="text-white font-bold text-[14px] tracking-tight leading-none">LotSync</div>
            <div className="text-white/30 text-[9px] font-bold tracking-widest uppercase mt-0.5">OMS</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-3 overflow-y-auto space-y-0.5" style={{ scrollbarWidth: 'none' }}>
        {items.map(item => {
          const active = activeNav === item.id
          return (
            <button key={item.id} onClick={() => onNav(item.id)}
              className="w-full flex items-center gap-3 px-2.5 py-2 rounded-md text-left transition-all duration-150"
              style={{ backgroundColor: active ? '#1D4ED8' : 'transparent', color: active ? '#fff' : 'rgba(255,255,255,0.55)' }}
              onMouseEnter={e => { if (!active) (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#162236' }}
              onMouseLeave={e => { if (!active) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent' }}>
              <span style={{ color: active ? '#fff' : 'rgba(255,255,255,0.4)', flexShrink: 0 }}>{item.icon}</span>
              <span className="text-[13px] font-medium truncate">{item.label}</span>
            </button>
          )
        })}
      </nav>

      {/* User */}
      <div className="px-3 pb-4 pt-2 border-t border-white/10">
        <button onClick={() => onNav('profile')}
          className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md transition-all text-left"
          style={{ backgroundColor: activeNav === 'profile' ? '#1D4ED8' : 'transparent' }}
          onMouseEnter={e => { if (activeNav !== 'profile') (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#162236' }}
          onMouseLeave={e => { if (activeNav !== 'profile') (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent' }}>
          <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-[11px] font-bold flex-shrink-0" style={{ backgroundColor: cfg.color }}>
            {cfg.initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-white text-[12px] font-semibold truncate">{cfg.name}</div>
            <div className="text-white/35 text-[10px] truncate">{cfg.title}</div>
          </div>
          <svg width="10" height="10" fill="none" viewBox="0 0 24 24" className="flex-shrink-0 text-white/30">
            <path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>
    </aside>
  )
}

// ─── Role Switcher Dropdown ───────────────────────────────────────────────────

function RoleSwitcher({ currentRole, onSwitch }: { currentRole: Role; onSwitch: (r: Role) => void }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const cfg = roleConfig[currentRole]

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 cursor-pointer group pl-2 py-1 rounded-lg hover:bg-slate-100 transition-colors">
        <div className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-white text-[10px] font-bold" style={{ backgroundColor: cfg.color }}>
          {cfg.initials}
        </div>
        <div className="text-left">
          <div className="text-[12px] font-bold text-slate-900 leading-none">{cfg.name}</div>
          <div className="text-[10px] text-slate-400">{cfg.title}</div>
        </div>
        <svg width="12" height="12" fill="none" viewBox="0 0 24 24" className="text-slate-400 ml-0.5">
          <path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-72 bg-white rounded-2xl border border-slate-200 shadow-xl shadow-slate-900/10 z-50 py-2 overflow-hidden">
          <div className="px-4 py-2 border-b border-slate-100 mb-1">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Switch Role — Prototype</div>
          </div>
          {roleOrder.map(role => {
            const rc = roleConfig[role]
            const isActive = role === currentRole
            return (
              <button key={role} onClick={() => { onSwitch(role); setOpen(false) }}
                className={`w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 transition-colors ${isActive ? 'bg-blue-50/60' : ''}`}>
                <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-bold flex-shrink-0"
                  style={{ backgroundColor: rc.color }}>
                  {rc.initials}
                </div>
                <div className="flex-1 text-left min-w-0">
                  <div className={`text-[13px] font-bold ${isActive ? 'text-blue-700' : 'text-slate-900'}`}>{role}</div>
                  <div className="text-[11px] text-slate-400 truncate">{rc.name}</div>
                </div>
                {isActive && (
                  <svg width="14" height="14" fill="none" viewBox="0 0 24 24">
                    <path d="M20 6 9 17l-5-5" stroke="#2563EB" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Header ───────────────────────────────────────────────────────────────────

// Demo Polish: this pill used to be a permanent, hardcoded "Systems
// Healthy" -- it never once reflected a real problem, even while the
// Dashboard directly below it (Dashboard.tsx) computed and displayed
// the real answer. Two status indicators on screen that can disagree
// is worse than one that's occasionally amber; this one is now driven
// by the same GET /dashboard connected_systems data.
const syncBadgeTone: Record<'green' | 'amber' | 'slate', string> = {
  green: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  amber: 'text-amber-700 bg-amber-50 border-amber-200',
  slate: 'text-slate-500 bg-slate-100 border-slate-200',
}
const syncBadgeDot: Record<'green' | 'amber' | 'slate', string> = {
  green: 'bg-emerald-400', amber: 'bg-amber-400', slate: 'bg-slate-400',
}

function Header({ role, onSwitch, onVehicleSelect }: { role: Role; onSwitch: (r: Role) => void; onVehicleSelect: (s: string) => void }) {
  const [search, setSearch] = useState('')
  const dashboardState = useApi(() => getDashboard(), [])

  const handleKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && search.trim()) {
      const q = search.trim().toUpperCase()
      // Widened from {4,8} (Sprint 3): onVehicleSelect now expects a VIN for
      // any caller wired to the real backend (GET /vehicles/{vin} is the
      // only vehicle lookup the API exposes -- there's no by-stock-number
      // endpoint). A full VIN is typically 17 chars; still accepts the
      // shorter stock-number shape too, which will just surface Vehicle
      // Detail's "not found" state until a stock->VIN lookup exists.
      if (/^[A-Z0-9]{4,17}$/.test(q)) { onVehicleSelect(q); setSearch('') }
    }
  }

  const systemEntries = dashboardState.status === 'success' ? Object.entries(dashboardState.data.connected_systems) : []
  const hasSyncIssue = systemEntries.some(([, s]) => s.status !== 'complete')
  const lastSyncAt = systemEntries.reduce<string | null>((latest, [, s]) => {
    const candidate = s.completed_at ?? s.started_at
    if (!candidate) return latest
    if (!latest || new Date(candidate) > new Date(latest)) return candidate
    return latest
  }, null)

  const syncBadge: { tone: 'green' | 'amber' | 'slate'; label: string } | null =
    dashboardState.status === 'error' ? { tone: 'slate', label: 'Sync Status Unavailable' }
    : dashboardState.status !== 'success' ? null
    : systemEntries.length === 0 ? { tone: 'slate', label: 'No Syncs Yet' }
    : hasSyncIssue ? { tone: 'amber', label: 'Sync Attention Needed' }
    : { tone: 'green', label: 'Systems Healthy' }

  return (
    <header className="bg-white border-b border-slate-200 flex items-center px-5 gap-3 flex-shrink-0" style={{ height: '52px' }}>
      {/* Search */}
      <div className="relative w-72">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
          <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8"/><path d="m16.5 16.5 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
        </span>
        <input value={search} onChange={e => setSearch(e.target.value)} onKeyDown={handleKey}
          type="text" placeholder="Search VIN, Stock #, Customer…"
          className="w-full h-8 pl-8 pr-10 text-[13px] bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all" />
        <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 bg-white border border-slate-200 rounded px-1 font-mono">⌘K</kbd>
      </div>

      <div className="flex-1" />

      {/* Systems status -- live, see syncBadge above */}
      {syncBadge && (
        <div className={`flex items-center gap-1.5 text-[12px] font-semibold border px-3 py-1 rounded-full ${syncBadgeTone[syncBadge.tone]}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${syncBadgeDot[syncBadge.tone]}`} />
          {syncBadge.label}
        </div>
      )}

      {/* Sync timestamp -- live */}
      {lastSyncAt && (
        <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
          <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M23 4v6h-6M1 20v-6h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
          Synced <span className="font-semibold text-slate-700 ml-1">{relativeTime(lastSyncAt)}</span>
        </div>
      )}

      <div className="w-px h-5 bg-slate-200 mx-1" />

      {/* Notifications */}
      <button className="relative w-8 h-8 flex items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 transition-colors">
        <svg width="15" height="15" fill="none" viewBox="0 0 24 24"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/></svg>
        <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white" />
      </button>

      {/* Role switcher */}
      <RoleSwitcher currentRole={role} onSwitch={onSwitch} />
    </header>
  )
}

// ─── Nav content ─────────────────────────────────────────────────────────────

function NavContent({ role, activeNav, onVehicleSelect, onNavigate }: {
  role: Role
  activeNav: string
  onVehicleSelect: (s: string) => void
  onNavigate: (tab: 'tasks' | 'inventory-sync') => void
}) {
  if (activeNav === 'vehicles')        return <VehiclesList onVehicleSelect={onVehicleSelect} />
  if (activeNav === 'tasks')           return <Tasks onVehicleSelect={onVehicleSelect} />
  if (activeNav === 'inventory-sync')  return <InventorySync />
  if (activeNav === 'profile')         return <Profile />
  return <Dashboard role={role} onVehicleSelect={onVehicleSelect} onNavigate={onNavigate} />
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [role, setRole] = useState<Role>('Lot Staff')
  const [activeNav, setActiveNav] = useState('dashboard')
  const [selectedVehicle, setSelectedVehicle] = useState<string | null>(null)

  const handleRoleSwitch = useCallback((r: Role) => {
    setRole(r)
    const firstNav = NAV[roleConfig[r].navGroup]?.[0]?.id ?? 'dashboard'
    setActiveNav(firstNav)
    setSelectedVehicle(null)
  }, [])

  const handleVehicleSelect = useCallback((stock: string) => {
    setSelectedVehicle(stock)
  }, [])

  const handleBack = useCallback(() => {
    setSelectedVehicle(null)
  }, [])

  // Keep breadcrumb label consistent with the tab the user came from
  const backLabel = activeNav === 'vehicles' ? 'Vehicles' : 'Dashboard'

  return (
    <div className="flex h-screen overflow-hidden" style={{ fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif", backgroundColor: '#F8FAFC' }}>
      <Sidebar role={role} activeNav={activeNav} onNav={setActiveNav} />

      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Header role={role} onSwitch={handleRoleSwitch} onVehicleSelect={handleVehicleSelect} />

        <div key={`${role}-${activeNav}-${selectedVehicle ?? 'dash'}`} className="flex-1 flex flex-col overflow-hidden min-h-0"
          style={{ animation: 'fadeSlideIn 0.18s ease-out' }}>
          {selectedVehicle
            // Sprint 3: Vehicle Detail is wired to GET /vehicles/{vin} --
            // selectedVehicle must be a VIN for this to resolve. Callers
            // still passing a stock number (any dashboard not yet
            // integrated this sprint) will see Vehicle Detail's own
            // "not found" state rather than a crash -- see
            // PHASE_3_SPRINT_3_REVIEW.md for which callers were updated.
            ? <VehicleDetailPage vin={selectedVehicle} onBack={handleBack} backLabel={backLabel} />
            : <NavContent role={role} activeNav={activeNav} onVehicleSelect={handleVehicleSelect} onNavigate={setActiveNav} />
          }
        </div>
      </div>
    </div>
  )
}
