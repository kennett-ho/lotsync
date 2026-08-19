/**
 * Sprint 12 (Rail C) -- the role-resolved navigation model.
 *
 * Pure data, no JSX: App.tsx maps these ids to icons/components. The
 * role ALWAYS comes from the server-confirmed /me identity
 * (AccessProvider) -- there is no client-side role selection anywhere,
 * and nothing here grants ability: every action stays authorized
 * server-side (api/auth.py) exactly as before this sprint.
 *
 * THE PRODUCTION-SAFETY INVARIANT: with auth disabled (today's
 * production posture) or any unresolved/unknown role, `GENERIC_NAV` /
 * `GENERIC_LANDING` reproduce the pre-Sprint-12 shell byte-for-byte
 * (same four items, same labels, same order, Dashboard landing, no
 * onboarding). Role-aware presentation activates ONLY on a
 * server-confirmed role -- and presentation falls back to the generic
 * shape, never to a privileged one. Pinned by
 * tests/test_frontend_role_ux.py.
 *
 * Rationale per role (full reasoning in ROLE_AWARE_UX.md SS2-3):
 * - manager/admin answer "what needs attention?" -> Overview first,
 *   with Inventory Sync control and (via Profile) User Management.
 * - lot_staff answers "what do I do, on which vehicle, why?" ->
 *   Today's Work first. The Inventory Sync NAV ITEM is omitted
 *   because every action on that surface 403s for this role (a
 *   standing dead end -- see the Phase 1 audit SS1.9); the evidence
 *   it carries stays reachable on Vehicle Detail and the header sync
 *   badge. Omission is presentation; SYNC_RUN_ROLES stays the
 *   security boundary.
 * - sales_manager has no invented workflow: shared surfaces, honest.
 */

export type NavId = 'dashboard' | 'today' | 'vehicles' | 'tasks' | 'inventory-sync'

export interface RoleNavItem { id: NavId; label: string }

/** Byte-identical to the pre-Sprint-12 fixed nav (App.tsx's old NAV_ITEMS). */
export const GENERIC_NAV: RoleNavItem[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'vehicles', label: 'Vehicles' },
  { id: 'tasks', label: 'Tasks' },
  { id: 'inventory-sync', label: 'Inventory Sync' },
]
export const GENERIC_LANDING: NavId = 'dashboard'

const MANAGER_NAV: RoleNavItem[] = [
  { id: 'dashboard', label: 'Overview' },
  { id: 'tasks', label: 'Tasks' },
  { id: 'vehicles', label: 'Vehicles' },
  { id: 'inventory-sync', label: 'Inventory Sync' },
]

const LOT_STAFF_NAV: RoleNavItem[] = [
  { id: 'today', label: "Today's Work" },
  { id: 'vehicles', label: 'Vehicles' },
  { id: 'tasks', label: 'Tasks' },
]

const SALES_MANAGER_NAV: RoleNavItem[] = [
  { id: 'dashboard', label: 'Overview' },
  { id: 'vehicles', label: 'Vehicles' },
  { id: 'tasks', label: 'Tasks' },
]

/**
 * Presentation-layer mirrors of the server role sets, used ONLY to
 * decide what to display (e.g. the Help page's Inventory Sync
 * section). The server enforces the real thing per request.
 */
export const SYNC_CONTROL_ROLES = ['admin', 'manager']
export const USER_ADMIN_ROLES = ['admin', 'manager']

export function navForRole(role: string | undefined): RoleNavItem[] {
  switch (role) {
    case 'admin':
    case 'manager':
      return MANAGER_NAV
    case 'lot_staff':
      return LOT_STAFF_NAV
    case 'sales_manager':
      return SALES_MANAGER_NAV
    default:
      return GENERIC_NAV
  }
}

export function landingForRole(role: string | undefined): NavId {
  return role === 'lot_staff' ? 'today' : GENERIC_LANDING
}
