/**
 * Sprint 14 (Rail J) -- ONE shared GET /dashboard per view, not one
 * per component. The header's live systems badge, the Overview, and
 * Today's Work all read the same connected_systems data; before this
 * provider each mounted its own useApi(getDashboard), so every landing
 * paid the request twice (measured live on deployed DEV: /dashboard
 * ×2 on both role landings) and the header's copy then went stale for
 * the rest of the session (it mounted once and never refetched).
 *
 * Freshness semantics are preserved, not weakened: surfaces that used
 * to fetch-on-mount now call refreshOnMount, which re-runs the shared
 * fetch UNLESS one is already in flight (that dedup is the whole
 * fix). The header consumes passively and now UPDATES whenever any
 * surface refreshes -- strictly fresher than before. This is
 * in-memory request sharing within one page view; nothing is cached
 * across views or persisted (the API stays Cache-Control: no-store
 * per SECURITY_ARCHITECTURE.md).
 */

import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { getDashboard } from './dashboard'
import { useApi, type ApiState } from './useApi'
import type { DashboardSummaryDTO } from './types'

interface DashboardData {
  state: ApiState<DashboardSummaryDTO>
  refresh: () => void
}

const DashboardDataContext = createContext<DashboardData>({
  state: { status: 'loading' },
  refresh: () => {},
})

export function DashboardDataProvider({ children }: { children: React.ReactNode }) {
  const [tick, setTick] = useState(0)
  const state = useApi(() => getDashboard(), [tick])

  // refresh() must be able to see the CURRENT status without being
  // recreated per state change (consumers depend on its identity in
  // effects), so the status rides a ref.
  const statusRef = useRef(state.status)
  statusRef.current = state.status

  const refresh = useCallback(() => {
    // A fetch already in flight will deliver data at least as fresh
    // as one started now -- starting a second concurrent request is
    // exactly the duplication this provider exists to remove.
    if (statusRef.current === 'loading') return
    setTick(t => t + 1)
  }, [])

  return (
    <DashboardDataContext.Provider value={{ state, refresh }}>
      {children}
    </DashboardDataContext.Provider>
  )
}

/**
 * Read the shared dashboard state. Pass refreshOnMount for surfaces
 * that previously fetched their own copy on mount (Overview, Today's
 * Work, Inventory Sync) so navigating to them still re-reads the
 * world; leave it false for passive consumers (the header).
 */
export function useDashboardData(refreshOnMount = false): DashboardData {
  const data = useContext(DashboardDataContext)
  const { refresh } = data
  useEffect(() => {
    if (refreshOnMount) refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshOnMount, refresh])
  return data
}
