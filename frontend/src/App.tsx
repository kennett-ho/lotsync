import { useState, useCallback } from 'react'
import VehicleDetailPage from './VehicleDetail'
import Dashboard from './dashboards/Dashboard'
import VehiclesList from './dashboards/VehiclesList'
import Tasks from './dashboards/Tasks'
import InventorySync from './dashboards/InventorySync'
import Profile from './dashboards/Profile'
import { getDashboard } from './api/dashboard'
import { useApi } from './api/useApi'
import IdentityFooter from './auth/IdentityFooter'
import { isAuthEnabled as IS_AUTH_ENABLED } from './auth/supabase'

// ─── Types ────────────────────────────────────────────────────────────────────

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

// Friday MVP: one nav, one workflow. Lot staff are the primary users;
// other departments contribute through this same operational workflow
// rather than a separate per-role workspace, so there's no branching
// here -- just the fixed set of screens every user sees.
const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard',     label: 'Dashboard',      icon: svgIcon('M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z') },
  { id: 'vehicles',      label: 'Vehicles',        icon: svgIcon('M5 17H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h13l4 4v4a2 2 0 0 1-2 2h-2', 'M5 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0zM15 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0z') },
  { id: 'tasks',         label: 'Tasks',           icon: svgIcon('M9 11l3 3L22 4', 'M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11') },
  { id: 'inventory-sync',label: 'Inventory Sync',  icon: svgIcon('M23 4v6h-6M1 20v-6h6', 'M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15') },
]

// ─── Development environment banner ──────────────────────────────────────────

// Sprint 02 (DealerDOH development environment): a deployment that
// identifies itself as development shows a permanent banner so it can
// never be mistaken for the production LotSync app a dealership is
// actively using. Driven by VITE_ENVIRONMENT=development, set only on
// the development Vercel project (baked in at build time, same as
// VITE_API_BASE_URL -- see src/api/client.ts). Production builds don't
// define it, so this renders nothing there.
const IS_DEV_ENVIRONMENT =
  ((import.meta as unknown as { env?: Record<string, string | undefined> }).env
    ?.VITE_ENVIRONMENT ?? '') === 'development'

function DevBanner() {
  return (
    <div
      className="flex-shrink-0 text-center"
      style={{
        backgroundColor: '#6D28D9',
        color: '#FFFFFF',
        fontSize: '12px',
        fontWeight: 600,
        letterSpacing: '0.04em',
        padding: '4px 12px',
      }}
    >
      DealerDOH DEV — Development Environment — Synthetic/Test Data Only
    </div>
  )
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

// lg (1024px) is this app's one "does it feel like the desktop shell"
// breakpoint -- used consistently for the sidebar/drawer switch here and
// for every other major panel-split across the dashboards, so mobile and
// tablet don't end up with several different cutover points (a second UI
// language by accident). Below lg, the permanent sidebar becomes an
// off-canvas drawer opened by Header's hamburger button; the drawer
// closes itself on nav so a one-handed user doesn't have to dismiss it
// separately.
function Sidebar({ activeNav, onNav, mobileOpen, onCloseMobile }: {
  activeNav: string; onNav: (id: string) => void; mobileOpen: boolean; onCloseMobile: () => void
}) {
  const items = NAV_ITEMS

  const handleNav = (id: string) => {
    onNav(id)
    onCloseMobile()
  }

  return (
    <>
      {mobileOpen && (
        <div className="fixed inset-0 bg-slate-900/50 z-30 lg:hidden" onClick={onCloseMobile} aria-hidden="true" />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 flex-shrink-0 flex flex-col h-screen transform transition-transform duration-200 ease-out
          lg:static lg:z-auto lg:w-52 lg:translate-x-0
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}
        style={{ backgroundColor: '#0B1629' }}>
        {/* Logo */}
        <div className="px-4 pt-5 pb-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 overflow-hidden">
              <img src="/img/logo/lotsynclogo.png" alt="LotSync" className="w-full h-full object-contain" />
            </div>
            <div className="text-white font-bold text-[24px] tracking-tight leading-none">LotSync</div>
          </div>
          <button onClick={onCloseMobile} aria-label="Close menu"
            className="lg:hidden w-8 h-8 flex items-center justify-center rounded-md text-white/50 hover:text-white hover:bg-white/10 transition-colors">
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-3 overflow-y-auto space-y-0.5" style={{ scrollbarWidth: 'none' }}>
          {items.map(item => {
            const active = activeNav === item.id
            return (
              <button key={item.id} onClick={() => handleNav(item.id)}
                className="w-full flex items-center gap-3 px-2.5 py-2.5 lg:py-2 rounded-md text-left transition-all duration-150"
                style={{ backgroundColor: active ? '#1D4ED8' : 'transparent', color: active ? '#fff' : 'rgba(255,255,255,0.55)' }}
                onMouseEnter={e => { if (!active) (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#162236' }}
                onMouseLeave={e => { if (!active) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent' }}>
                <span style={{ color: active ? '#fff' : 'rgba(255,255,255,0.4)', flexShrink: 0 }}>{item.icon}</span>
                <span className="text-[13px] font-medium truncate">{item.label}</span>
              </button>
            )
          })}
        </nav>

        {/* Sprint 05: when auth is enabled, the signed-in identity
            (email · role · dealership, from GET /me) plus Sign Out
            live here -- see auth/IdentityFooter.tsx. Renders nothing
            in unauthenticated builds (production). */}
        {IS_AUTH_ENABLED && <IdentityFooter />}

        {/* Profile & Settings entry point -- no user identity displayed here,
            just a generic icon/label; see Profile.tsx for the page itself. */}
        <div className="px-3 pb-4 pt-2 border-t border-white/10">
          <button onClick={() => handleNav('profile')}
            className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md transition-all text-left"
            style={{ backgroundColor: activeNav === 'profile' ? '#1D4ED8' : 'transparent' }}
            onMouseEnter={e => { if (activeNav !== 'profile') (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#162236' }}
            onMouseLeave={e => { if (activeNav !== 'profile') (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent' }}>
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-white/70 flex-shrink-0" style={{ backgroundColor: '#1E293B' }}>
              <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/><circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="1.75"/></svg>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white text-[12px] font-semibold truncate">Profile &amp; Settings</div>
            </div>
            <svg width="10" height="10" fill="none" viewBox="0 0 24 24" className="flex-shrink-0 text-white/30">
              <path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>

        {/* A tiny, tasteful signature -- not branding. Sits beneath the
            nav/profile block so it never competes with anything
            interactive; low enough contrast (white/15 at 9px) to read
            as an easter egg, not a footer. */}
        <div className="px-4 pb-3 pt-1 flex-shrink-0">
          <p className="text-[9px] text-white/15 leading-tight select-none">Developed by Kennett Ho</p>
        </div>
      </aside>
    </>
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

function Header({ onVehicleSelect, onOpenMobileNav }: { onVehicleSelect: (s: string) => void; onOpenMobileNav: () => void }) {
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
    <header className="bg-white border-b border-slate-200 flex items-center px-3 sm:px-5 gap-2 sm:gap-3 flex-shrink-0" style={{ height: '52px' }}>
      {/* Hamburger -- opens the off-canvas drawer below lg; the permanent
          sidebar takes over at lg, so this button simply doesn't render there. */}
      <button onClick={onOpenMobileNav} aria-label="Open menu"
        className="lg:hidden flex-shrink-0 w-9 h-9 flex items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 transition-colors">
        <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round"/></svg>
      </button>

      {/* Search -- fills available width on mobile, fixed 288px from lg up
          (unchanged desktop sizing). ⌘K hint hidden below lg -- a keyboard
          shortcut hint is meaningless on a touch device and just costs space. */}
      <div className="relative flex-1 min-w-0 lg:flex-none lg:w-72">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
          <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8"/><path d="m16.5 16.5 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
        </span>
        <input value={search} onChange={e => setSearch(e.target.value)} onKeyDown={handleKey}
          type="text" placeholder="Search VIN, Stock #, Customer…"
          className="w-full h-8 pl-8 pr-3 lg:pr-10 text-[13px] bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all" />
        <kbd className="hidden lg:block absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 bg-white border border-slate-200 rounded px-1 font-mono">⌘K</kbd>
      </div>

      <div className="flex-1 hidden sm:block" />

      {/* Systems status -- live, see syncBadge above. Hidden below sm --
          the notification bell already carries the "something needs
          attention" signal at the narrowest widths. */}
      {syncBadge && (
        <div className={`hidden sm:flex items-center gap-1.5 text-[12px] font-semibold border px-3 py-1 rounded-full ${syncBadgeTone[syncBadge.tone]}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${syncBadgeDot[syncBadge.tone]}`} />
          {syncBadge.label}
        </div>
      )}

      {/* Sync timestamp -- live; hidden below lg, least essential item when space is tight */}
      {lastSyncAt && (
        <div className="hidden lg:flex items-center gap-1.5 text-[11px] text-slate-500">
          <svg width="12" height="12" fill="none" viewBox="0 0 24 24"><path d="M23 4v6h-6M1 20v-6h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
          Synced <span className="font-semibold text-slate-700 ml-1">{relativeTime(lastSyncAt)}</span>
        </div>
      )}

      {/* Sprint 09: the notification bell (with its permanent fake red
          dot) is removed under the settings-honesty rule -- no
          notification system exists yet (Rail E is CONDITIONAL in
          V1_1_RELEASE_READINESS.md). It returns with the real feature. */}
    </header>
  )
}

// ─── Nav content ─────────────────────────────────────────────────────────────

function NavContent({ activeNav, onVehicleSelect, onNavigate }: {
  activeNav: string
  onVehicleSelect: (s: string) => void
  onNavigate: (tab: 'tasks' | 'inventory-sync') => void
}) {
  if (activeNav === 'vehicles')        return <VehiclesList onVehicleSelect={onVehicleSelect} />
  if (activeNav === 'tasks')           return <Tasks onVehicleSelect={onVehicleSelect} />
  if (activeNav === 'inventory-sync')  return <InventorySync />
  if (activeNav === 'profile')         return <Profile />
  return <Dashboard onVehicleSelect={onVehicleSelect} onNavigate={onNavigate} />
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [activeNav, setActiveNav] = useState('dashboard')
  const [selectedVehicle, setSelectedVehicle] = useState<string | null>(null)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  const handleVehicleSelect = useCallback((stock: string) => {
    setSelectedVehicle(stock)
    setMobileNavOpen(false)
  }, [])

  const handleBack = useCallback(() => {
    setSelectedVehicle(null)
  }, [])

  // Keep breadcrumb label consistent with the tab the user came from
  const backLabel = activeNav === 'vehicles' ? 'Vehicles' : 'Dashboard'

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif", backgroundColor: '#F8FAFC' }}>
      {IS_DEV_ENVIRONMENT && <DevBanner />}

      <div className="flex flex-1 overflow-hidden min-h-0">
        <Sidebar activeNav={activeNav} onNav={setActiveNav} mobileOpen={mobileNavOpen} onCloseMobile={() => setMobileNavOpen(false)} />

        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          <Header onVehicleSelect={handleVehicleSelect} onOpenMobileNav={() => setMobileNavOpen(true)} />

          <div key={`${activeNav}-${selectedVehicle ?? 'dash'}`} className="flex-1 flex flex-col overflow-hidden min-h-0"
            style={{ animation: 'fadeSlideIn 0.18s ease-out' }}>
            {selectedVehicle
              // Sprint 3: Vehicle Detail is wired to GET /vehicles/{vin} --
              // selectedVehicle must be a VIN for this to resolve. Callers
              // still passing a stock number (any dashboard not yet
              // integrated this sprint) will see Vehicle Detail's own
              // "not found" state rather than a crash -- see
              // PHASE_3_SPRINT_3_REVIEW.md for which callers were updated.
              ? <VehicleDetailPage vin={selectedVehicle} onBack={handleBack} backLabel={backLabel} />
              : <NavContent activeNav={activeNav} onVehicleSelect={handleVehicleSelect} onNavigate={setActiveNav} />
            }
          </div>
        </div>
      </div>
    </div>
  )
}
