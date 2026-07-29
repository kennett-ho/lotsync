import { useEffect, useState, type DependencyList } from 'react'
import { ApiError } from './client'

export type ApiState<T> =
  | { status: 'loading' }
  | { status: 'error'; error: ApiError }
  | { status: 'success'; data: T }

/**
 * The one reusable data-fetching hook every screen in this sprint uses
 * to call the backend. Centralizes loading/error handling so screens
 * only decide how to *render* each state (per this sprint's "React as
 * a presentation layer only" instruction) -- no screen should hand-roll
 * its own useState/useEffect fetch pair.
 *
 * `deps` follows useEffect's own rules -- pass the values the fetch
 * depends on (e.g. a vin) so it refetches when they change.
 */
export function useApi<T>(fetcher: () => Promise<T>, deps: DependencyList): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading' })

    fetcher()
      .then((data) => {
        if (!cancelled) setState({ status: 'success', data })
      })
      .catch((error: unknown) => {
        if (cancelled) return
        const apiError =
          error instanceof ApiError ? error : new ApiError('Unexpected error', -1)
        setState({ status: 'error', error: apiError })
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return state
}
