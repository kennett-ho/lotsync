import { Suspense, lazy, useCallback, useEffect, useRef, useState } from 'react'
import { track } from './observability/analytics'
import VehicleDetailPage from './VehicleDetail'
import Dashboard from './dashboards/Dashboard'
import VehiclesList from './dashboards/VehiclesList'
import Tasks from './dashboards/Tasks'
import TodaysWork from './dashboards/TodaysWork'
import { getOnboardingRecord, recordOnboardingComplete } from './onboarding/state'
import { DashboardDataProvider, useDashboardData } from './api/dashboardData'
import { useAccess, useMe } from './auth/AccessProvider'
import IdentityFooter from './auth/IdentityFooter'
import { isAuthEnabled as IS_AUTH_ENABLED } from './auth/supabase'
import { landingForRole, navForRole, type RoleNavItem } from './roleNav'

// Sprint 14 (Rail J): surfaces that are role-gated or reached rarely
// load as their own chunks -- the landing experiences (Overview,
// Today's Work, Vehicles, Tasks, Vehicle Detail) stay in the initial
// bundle deliberately so first use never waits on a second fetch.
const InventorySync = lazy(() => import('./dashboards/InventorySync'))
const Profile = lazy(() => import('./dashboards/Profile'))
const Help = lazy(() => import('./help/Help'))
const Onboarding = lazy(() => import('./onboarding/Onboarding'))

// ─── Types ────────────────────────────────────────────────────────────────────

interface NavItem { id: string; label: string; icon: JSX.Element }

function svgIcon(d: string, d2?: string) {
  return (
    <svg width="15" height="15" fill="none" viewBox="0 0 24 24" aria-hidden="true">
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

// Sprint 12 (Rail C): the nav is role-resolved -- ORDER, LABELS, and
// VISIBILITY come from roleNav.ts keyed on the server-confirmed /me
// role; icons stay here because they're JSX. With auth disabled
// (production) or no resolved role, roleNav's GENERIC_NAV reproduces
// the pre-Sprint-12 fixed nav exactly. Presentation only: hiding an
// item never revokes or grants anything server-side.
const NAV_ICONS: Record<string, JSX.Element> = {
  dashboard:        svgIcon('M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z'),
  today:            svgIcon('M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z', 'M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41'),
  vehicles:         svgIcon('M5 17H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h13l4 4v4a2 2 0 0 1-2 2h-2', 'M5 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0zM15 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0z'),
  tasks:            svgIcon('M9 11l3 3L22 4', 'M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11'),
  'inventory-sync': svgIcon('M23 4v6h-6M1 20v-6h6', 'M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15'),
}

function toNavItems(items: RoleNavItem[]): NavItem[] {
  return items.map(item => ({ id: item.id, label: item.label, icon: NAV_ICONS[item.id] }))
}

// Sprint 14 (Rail K): the document title names the current surface so
// browser tabs, history, and screen-reader window announcements are
// distinguishable. Controlled labels only -- never a VIN or stock
// number. The base title comes from the built document shell
// (.figma/make/site.json); taking the LAST " · " segment makes the
// capture idempotent when dev-mode HMR re-evaluates this module after
// a surface title was already applied.
const BASE_TITLE =
  (typeof document !== 'undefined' && document.title
    ? document.title.split(' · ').pop() : undefined) || 'LotSync'

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
//
// Sprint 14 (Rail K): while CLOSED below lg the drawer is `inert`, so
// its controls leave the tab order and accessibility tree -- previously
// a keyboard user tabbed through six off-screen buttons. Opening moves
// focus to the close button; Escape closes and App returns focus to
// the hamburger. (inert rather than a visibility transition: it is
// deterministic, and the slide stays a pure transform animation.)
function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(min-width: 1024px)').matches,
  )
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)')
    const onChange = () => setIsDesktop(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return isDesktop
}

function Sidebar({ items, activeNav, onNav, mobileOpen, onCloseMobile }: {
  items: NavItem[]; activeNav: string; onNav: (id: string) => void; mobileOpen: boolean; onCloseMobile: () => void
}) {
  const isDesktop = useIsDesktop()
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const wasOpen = useRef(false)
  useEffect(() => {
    if (mobileOpen && !wasOpen.current) closeButtonRef.current?.focus()
    wasOpen.current = mobileOpen
  }, [mobileOpen])

  const handleNav = (id: string) => {
    onNav(id)
    onCloseMobile()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && mobileOpen) {
      e.stopPropagation()
      onCloseMobile()
    }
  }

  return (
    <>
      {mobileOpen && (
        <div className="fixed inset-0 bg-slate-900/50 z-30 lg:hidden" onClick={onCloseMobile} aria-hidden="true" />
      )}
      <aside
        id="app-sidebar"
        aria-label="Sidebar"
        onKeyDown={handleKeyDown}
        inert={!isDesktop && !mobileOpen}
        className={`fixed inset-y-0 left-0 z-40 w-64 flex-shrink-0 flex flex-col h-screen transform transition-transform duration-200 ease-out
          lg:static lg:z-auto lg:w-52 lg:translate-x-0
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}
        style={{ backgroundColor: '#0B1629' }}>
        {/* Logo */}
        <div className="px-4 pt-5 pb-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 overflow-hidden">
              <img src="/img/logo/lotsynclogo.png" alt="" className="w-full h-full object-contain" />
            </div>
            <div className="text-white font-bold text-[24px] tracking-tight leading-none">LotSync</div>
          </div>
          <button onClick={onCloseMobile} aria-label="Close menu" ref={closeButtonRef}
            className="lg:hidden w-8 h-8 flex items-center justify-center rounded-md text-white/50 hover:text-white hover:bg-white/10 transition-colors">
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
          </button>
        </div>

        {/* Nav */}
        <nav aria-label="Main navigation" className="flex-1 px-3 py-3 overflow-y-auto space-y-0.5" style={{ scrollbarWidth: 'none' }}>
          {items.map(item => {
            const active = activeNav === item.id
            return (
              <button key={item.id} onClick={() => handleNav(item.id)}
                aria-current={active ? 'page' : undefined}
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

        {/* Sprint 12 (Rail B): Help & Getting Started -- every
            AUTHENTICATED role, beneath the operational nav. Gated like
            IdentityFooter: the unauthenticated production posture keeps
            its pre-Sprint-12 shell byte-for-byte (the invariant), and
            Help's copy assumes accounts/roles exist. */}
        {IS_AUTH_ENABLED && (
        <div className="px-3 pt-2 border-t border-white/10">
          <button onClick={() => handleNav('help')}
            aria-current={activeNav === 'help' ? 'page' : undefined}
            className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md transition-all text-left"
            style={{ backgroundColor: activeNav === 'help' ? '#1D4ED8' : 'transparent' }}
            onMouseEnter={e => { if (activeNav !== 'help') (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#162236' }}
            onMouseLeave={e => { if (activeNav !== 'help') (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent' }}>
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-white/70 flex-shrink-0" style={{ backgroundColor: '#1E293B' }}>
              <svg width="14" height="14" fill="none" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.75"/><path d="M9.5 9.3a2.6 2.6 0 0 1 5.1.6c0 1.6-2.4 2-2.4 3.3M12 16.8h.01" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/></svg>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white text-[12px] font-semibold truncate">Help</div>
            </div>
          </button>
        </div>
        )}

        {/* Profile & Settings entry point -- no user identity displayed here,
            just a generic icon/label; see Profile.tsx for the page itself. */}
        <div className={`px-3 pb-4 ${IS_AUTH_ENABLED ? 'pt-1' : 'pt-2 border-t border-white/10'}`}>
          <button onClick={() => handleNav('profile')}
            aria-current={activeNav === 'profile' ? 'page' : undefined}
            className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md transition-all text-left"
            style={{ backgroundColor: activeNav === 'profile' ? '#1D4ED8' : 'transparent' }}
            onMouseEnter={e => { if (activeNav !== 'profile') (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#162236' }}
            onMouseLeave={e => { if (activeNav !== 'profile') (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent' }}>
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-white/70 flex-shrink-0" style={{ backgroundColor: '#1E293B' }}>
              <svg width="14" height="14" fill="none" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/><circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="1.75"/></svg>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white text-[12px] font-semibold truncate">Profile &amp; Settings</div>
            </div>
            <svg width="10" height="10" fill="none" viewBox="0 0 24 24" className="flex-shrink-0 text-white/30" aria-hidden="true">
              <path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>

        {/* A tiny, tasteful signature -- not branding. Sits beneath the
            nav/profile block so it never competes with anything
            interactive. Sprint 14 (Rail K, owner decision): visible,
            meaningful attribution is TEXT, not decoration -- it meets
            AA contrast (white/50 on the sidebar navy ~5:1, the same
            quiet tone as the identity footer's secondary line) and is
            exposed to assistive technology. Subtlety comes from the
            9px size and placement, never from sub-AA contrast. */}
        <div className="px-4 pb-3 pt-1 flex-shrink-0">
          <p className="text-[9px] text-white/50 leading-tight select-none">Developed by Kennett Ho</p>
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
// Sprint 14 (Rail K): the slate tone is text-slate-600 -- slate-500 on
// slate-100 measures 4.34:1, just under AA. Found by re-running axe
// with the backend unreachable: the "Sync Status Unavailable" /
// "No Syncs Yet" states only render then, so data-full audit passes
// never painted them.
const syncBadgeTone: Record<'green' | 'amber' | 'slate', string> = {
  green: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  amber: 'text-amber-700 bg-amber-50 border-amber-200',
  slate: 'text-slate-600 bg-slate-100 border-slate-200',
}
const syncBadgeDot: Record<'green' | 'amber' | 'slate', string> = {
  green: 'bg-emerald-400', amber: 'bg-amber-400', slate: 'bg-slate-400',
}

function Header({ onVehicleSelect, onOpenMobileNav, mobileNavOpen, hamburgerRef }: {
  onVehicleSelect: (s: string) => void
  onOpenMobileNav: () => void
  mobileNavOpen: boolean
  hamburgerRef: React.RefObject<HTMLButtonElement | null>
}) {
  const [search, setSearch] = useState('')
  // Sprint 14 (Rail J): the shared per-view /dashboard state -- the
  // header consumes passively (surfaces own the refreshes), which
  // also means this badge now UPDATES when a surface refreshes
  // instead of staying frozen at its first mount.
  const dashboardState = useDashboardData().state

  // Sprint 12 (audit D2): the ⌘K hint used to be decorative -- no
  // handler existed. Now it does what it advertises: focus the search.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        document.getElementById('vehicle-search-input')?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const handleKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && search.trim()) {
      const q = search.trim().toUpperCase()
      // GET /vehicles/{vin} is the only lookup the API exposes -- the
      // placeholder now says exactly that (audit D2: it used to promise
      // Stock #/Customer search that never existed). A shorter
      // stock-number-shaped entry still resolves to Vehicle Detail's own
      // honest "not found" state rather than silently doing nothing.
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
      <button onClick={onOpenMobileNav} aria-label="Open menu" ref={hamburgerRef}
        aria-expanded={mobileNavOpen} aria-controls="app-sidebar"
        className="lg:hidden flex-shrink-0 w-9 h-9 flex items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 transition-colors">
        <svg width="18" height="18" fill="none" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round"/></svg>
      </button>

      {/* Search -- fills available width on mobile, fixed 288px from lg up
          (unchanged desktop sizing). ⌘K hint hidden below lg -- a keyboard
          shortcut hint is meaningless on a touch device and just costs space. */}
      <div className="relative flex-1 min-w-0 lg:flex-none lg:w-72">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true">
          <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8"/><path d="m16.5 16.5 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
        </span>
        <input value={search} onChange={e => setSearch(e.target.value)} onKeyDown={handleKey}
          id="vehicle-search-input"
          aria-label="Search vehicles by VIN"
          type="text" placeholder="Search by VIN…"
          className="w-full h-8 pl-8 pr-3 lg:pr-10 text-[13px] bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all" />
        <kbd className="hidden lg:block absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-slate-500 bg-white border border-slate-200 rounded px-1 font-mono" aria-hidden="true">⌘K</kbd>
      </div>

      <div className="flex-1 hidden sm:block" />

      {/* Systems status -- live, see syncBadge above. Hidden below sm --
          the notification bell already carries the "something needs
          attention" signal at the narrowest widths. */}
      {syncBadge && (
        <div className={`hidden sm:flex items-center gap-1.5 text-[12px] font-semibold border px-3 py-1 rounded-full ${syncBadgeTone[syncBadge.tone]}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${syncBadgeDot[syncBadge.tone]}`} aria-hidden="true" />
          {syncBadge.label}
        </div>
      )}

      {/* Sync timestamp -- live; hidden below lg, least essential item when space is tight */}
      {lastSyncAt && (
        <div className="hidden lg:flex items-center gap-1.5 text-[11px] text-slate-500">
          <svg width="12" height="12" fill="none" viewBox="0 0 24 24" aria-hidden="true"><path d="M23 4v6h-6M1 20v-6h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
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

function NavContent({ activeNav, onVehicleSelect, onNavigate, onReplayOnboarding }: {
  activeNav: string
  onVehicleSelect: (s: string) => void
  onNavigate: (tab: 'tasks' | 'inventory-sync') => void
  onReplayOnboarding: () => void
}) {
  if (activeNav === 'today')           return <TodaysWork onVehicleSelect={onVehicleSelect} />
  if (activeNav === 'vehicles')        return <VehiclesList onVehicleSelect={onVehicleSelect} />
  if (activeNav === 'tasks')           return <Tasks onVehicleSelect={onVehicleSelect} />
  if (activeNav === 'inventory-sync')  return <InventorySync />
  if (activeNav === 'profile')         return <Profile />
  if (activeNav === 'help')            return <Help onReplayOnboarding={onReplayOnboarding} />
  return <Dashboard onVehicleSelect={onVehicleSelect} onNavigate={onNavigate} />
}

// Fallback while a lazy surface chunk loads -- same quiet language as
// every other loading state; role=status so the wait is perceivable
// without vision.
function SurfaceFallback() {
  return (
    <div role="status" className="flex-1 flex items-center justify-center text-slate-500 text-[13px]">
      Loading…
    </div>
  )
}

// Document titles per surface -- controlled labels only (never a VIN).
const SURFACE_TITLES: Record<string, string> = {
  dashboard: 'Overview',
  today: "Today's Work",
  vehicles: 'Vehicles',
  tasks: 'Tasks',
  'inventory-sync': 'Inventory Sync',
  profile: 'Profile & Settings',
  help: 'Help',
}

// ─── App ──────────────────────────────────────────────────────────────────────

function AppShell() {
  const me = useMe()
  const { state: accessState } = useAccess()
  // The role is real only once the SERVER confirmed the membership --
  // with auth disabled (production) me stays null and everything below
  // resolves to the generic pre-Sprint-12 shape (roleNav.ts invariant).
  const role = me?.authenticated ? me.role : undefined

  const navItems = toNavItems(navForRole(role))

  // null = "the role's landing surface"; set only by explicit user
  // navigation. Role-aware landings never fight user intent.
  const [navChoice, setNavChoice] = useState<string | null>(null)
  const [selectedVehicle, setSelectedVehicle] = useState<string | null>(null)
  // The surface Vehicle Detail was opened FROM -- the breadcrumb tells
  // the truth about where Back goes (audit §1.6: it used to claim
  // "Dashboard" while landing elsewhere).
  const [vehicleOrigin, setVehicleOrigin] = useState<string | null>(null)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const hamburgerRef = useRef<HTMLButtonElement>(null)
  const mainRef = useRef<HTMLDivElement>(null)

  // A stale explicit choice (e.g. a surface this role's nav doesn't
  // offer, after a role resolves mid-session) falls back to the landing.
  const navIds = navItems.map(item => item.id) as string[]
  const validChoice = navChoice !== null && (navIds.includes(navChoice) || navChoice === 'profile' || navChoice === 'help')
  const activeNav = validChoice ? (navChoice as string) : landingForRole(role)

  // ─── Onboarding (Rail B) ──────────────────────────────────────────
  // 'unknown' until the stored record is read; first-run opens the
  // tour. Auth disabled -> onboarding does not exist (production
  // invariant). Skip records completion just like finishing
  // (ROLE_AWARE_UX.md S12-10); replay never re-writes the record.
  const [onboarding, setOnboarding] = useState<'unknown' | 'closed' | 'first-run' | 'replay'>('unknown')

  useEffect(() => {
    if (!IS_AUTH_ENABLED || !me?.authenticated) {
      if (!IS_AUTH_ENABLED) setOnboarding('closed')
      return
    }
    let cancelled = false
    getOnboardingRecord().then(record => {
      if (cancelled) return
      if (record) { setOnboarding('closed') }
      else {
        setOnboarding('first-run')
        track('onboarding_started')
      }
    })
    return () => { cancelled = true }
  }, [me?.authenticated])

  const finishOnboarding = useCallback(() => {
    if (onboarding === 'first-run') {
      void recordOnboardingComplete(false)
      track('onboarding_completed')
    }
    setOnboarding('closed')
  }, [onboarding])

  const skipOnboarding = useCallback(() => {
    if (onboarding === 'first-run') {
      void recordOnboardingComplete(true)
      track('onboarding_skipped')
    }
    setOnboarding('closed')
  }, [onboarding])

  const replayOnboarding = useCallback(() => {
    track('onboarding_replayed')
    setOnboarding('replay')
  }, [])

  // Sprint 11 (analytics): explicit page_viewed with CONTROLLED page
  // identifiers -- navigation here is state-based, so this effect is
  // the app's single "page changed" seam. Never a raw URL, never the
  // selected VIN; vehicle detail reports the page id only, with a
  // separate deliberate vehicle_detail_opened event.
  useEffect(() => {
    track('page_viewed', { page: selectedVehicle ? 'vehicle-detail' : activeNav })
    if (selectedVehicle) track('vehicle_detail_opened', { source: activeNav })
  }, [activeNav, selectedVehicle])

  // Sprint 14 (Rail K): the same seam keeps the document title naming
  // the current surface (controlled labels only).
  useEffect(() => {
    const label = selectedVehicle ? 'Vehicle Detail' : (SURFACE_TITLES[activeNav] ?? BASE_TITLE)
    document.title = label === BASE_TITLE ? BASE_TITLE : `${label} · ${BASE_TITLE}`
  }, [activeNav, selectedVehicle])

  const handleVehicleSelect = useCallback((stock: string) => {
    if (selectedVehicle === null) setVehicleOrigin(activeNav)
    setSelectedVehicle(stock)
    setMobileNavOpen(false)
  }, [activeNav, selectedVehicle])

  const handleBack = useCallback(() => {
    setSelectedVehicle(null)
    setVehicleOrigin(null)
  }, [])

  // Sprint 12 (audit §1.6 fix): navigating ALWAYS lands on the chosen
  // surface -- an open Vehicle Detail is dismissed instead of silently
  // swallowing the click.
  const handleNav = useCallback((id: string) => {
    setNavChoice(id)
    setSelectedVehicle(null)
    setVehicleOrigin(null)
  }, [])

  // Sprint 14 (Rail K): closing the mobile drawer returns focus to the
  // hamburger IF the close wasn't a navigation (the surface-change
  // effect below runs after this one in the same commit and wins focus
  // on nav, which is the right destination there).
  const drawerWasOpen = useRef(false)
  useEffect(() => {
    if (drawerWasOpen.current && !mobileNavOpen) hamburgerRef.current?.focus()
    drawerWasOpen.current = mobileNavOpen
  }, [mobileNavOpen])

  // Sprint 14 (Rail K): state navigation moves keyboard/AT reading
  // position to the new surface -- the SPA equivalent of a page load.
  // Keyed on the surface identity (not a first-render flag) so the
  // initial mount never steals focus, including under StrictMode's
  // double-invoked effects.
  const prevSurface = useRef<string | null>(null)
  useEffect(() => {
    const surfaceKey = `${activeNav}|${selectedVehicle ?? ''}`
    if (prevSurface.current !== null && prevSurface.current !== surfaceKey) {
      mainRef.current?.focus()
    }
    prevSurface.current = surfaceKey
  }, [activeNav, selectedVehicle])

  // Sprint 14 (Rail K): Escape closes an open Vehicle Detail (it
  // behaves as an overlay surface). The onboarding dialog and the
  // drawer handle their own Escape and stop propagation first.
  useEffect(() => {
    if (!selectedVehicle) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleBack()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selectedVehicle, handleBack])

  // Truthful breadcrumb: the label of the surface Vehicle Detail was
  // actually opened from.
  const originId = vehicleOrigin ?? activeNav
  const backLabel =
    navItems.find(item => item.id === originId)?.label
    ?? (originId === 'profile' ? 'Profile & Settings' : originId === 'help' ? 'Help' : 'Dashboard')

  // Auth-enabled builds briefly know nothing about the user while /me
  // resolves; rendering the generic shell then snapping to a role
  // layout reads as a glitch. A quiet splash instead. Disabled builds
  // (production) never hit this branch.
  if (IS_AUTH_ENABLED && accessState.status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center" role="status"
           style={{ backgroundColor: '#0B1220' }}>
        <div className="text-white/40 text-[13px]">Loading DealerDOH…</div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif", backgroundColor: '#F8FAFC' }}>
      {/* Sprint 14 (Rail K): keyboard bypass for the repeated sidebar/
          header blocks -- visually hidden until focused (index.css). */}
      <a href="#main-content" className="skip-link"
        onClick={e => { e.preventDefault(); mainRef.current?.focus() }}>
        Skip to main content
      </a>

      {IS_DEV_ENVIRONMENT && <DevBanner />}

      {(onboarding === 'first-run' || onboarding === 'replay') && (
        <Suspense fallback={null}>
          <Onboarding role={role} onFinish={finishOnboarding} onSkip={skipOnboarding} />
        </Suspense>
      )}

      <div className="flex flex-1 overflow-hidden min-h-0">
        {/* While a vehicle is open, the highlighted item is the surface
            it was opened from -- the same one Back returns to. */}
        <Sidebar items={navItems} activeNav={selectedVehicle ? originId : activeNav} onNav={handleNav}
          mobileOpen={mobileNavOpen} onCloseMobile={() => setMobileNavOpen(false)} />

        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          <Header onVehicleSelect={handleVehicleSelect} onOpenMobileNav={() => setMobileNavOpen(true)}
            mobileNavOpen={mobileNavOpen} hamburgerRef={hamburgerRef} />

          <main id="main-content" ref={mainRef} tabIndex={-1}
            key={`${activeNav}-${selectedVehicle ?? 'dash'}`}
            className="flex-1 flex flex-col overflow-hidden min-h-0 outline-none"
            style={{ animation: 'fadeSlideIn 0.18s ease-out' }}>
            {selectedVehicle
              // Sprint 3: Vehicle Detail is wired to GET /vehicles/{vin} --
              // selectedVehicle must be a VIN for this to resolve. Callers
              // still passing a stock number (any dashboard not yet
              // integrated this sprint) will see Vehicle Detail's own
              // "not found" state rather than a crash -- see
              // PHASE_3_SPRINT_3_REVIEW.md for which callers were updated.
              ? <VehicleDetailPage vin={selectedVehicle} onBack={handleBack} backLabel={backLabel} />
              : (
                <Suspense fallback={<SurfaceFallback />}>
                  <NavContent activeNav={activeNav} onVehicleSelect={handleVehicleSelect}
                    onNavigate={handleNav} onReplayOnboarding={replayOnboarding} />
                </Suspense>
              )
            }
          </main>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  // Sprint 14 (Rail J): every dashboard consumer under one shared
  // fetch -- see api/dashboardData.tsx.
  return (
    <DashboardDataProvider>
      <AppShell />
    </DashboardDataProvider>
  )
}
