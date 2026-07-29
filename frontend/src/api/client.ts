/**
 * The single fetch boundary between the frontend and the LotSync
 * FastAPI backend (api/app.py). No component should call `fetch`
 * directly against a backend route -- every request goes through
 * `apiGet` so a base-URL change, an auth header (Phase 3 later work),
 * or a response-shape correction only needs updating here.
 *
 * FastAPI is the single source of truth (per this sprint's own
 * instruction): this file does no business-logic interpretation of the
 * response, only network/transport concerns -- reachability, HTTP
 * status, JSON parsing.
 */

const DEFAULT_API_BASE_URL = 'http://localhost:8000'

// Overridable via a .env.local VITE_API_BASE_URL, same convention the
// backend already uses for LOTSYNC_* env vars -- not committed, since
// frontend/.gitignore already excludes .env* files project-wide.
export const API_BASE_URL: string =
  (import.meta as unknown as { env?: Record<string, string | undefined> }).env
    ?.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** True when the backend was unreachable at all (network/CORS failure), not just a non-2xx response. */
export function isBackendUnavailable(error: unknown): boolean {
  return error instanceof ApiError && error.status === 0
}

export async function apiGet<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined | null>,
): Promise<T> {
  const url = new URL(path, API_BASE_URL)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) url.searchParams.set(key, String(value))
    }
  }

  let response: Response
  try {
    response = await fetch(url.toString())
  } catch {
    throw new ApiError(
      `Could not reach the LotSync API at ${API_BASE_URL}. Is the backend running?`,
      0,
    )
  }

  if (response.status === 404) {
    throw new ApiError('Not found', 404)
  }
  if (!response.ok) {
    throw new ApiError(`LotSync API returned ${response.status} for ${path}`, response.status)
  }

  return (await response.json()) as T
}

/**
 * POST /inventory-sync/run's shape -- multipart form data in, JSON out.
 * This project's first write call, so its error handling goes slightly
 * further than apiGet's: FastAPI's HTTPException(detail=...) returns
 * either a string or a list of per-file validation problems (see
 * api/routers/inventory_sync.py) -- both are folded into one readable
 * ApiError message rather than left for every caller to re-parse.
 */
export async function apiPostForm<T>(path: string, formData: FormData): Promise<T> {
  const url = new URL(path, API_BASE_URL)

  let response: Response
  try {
    response = await fetch(url.toString(), { method: 'POST', body: formData })
  } catch {
    throw new ApiError(
      `Could not reach the LotSync API at ${API_BASE_URL}. Is the backend running?`,
      0,
    )
  }

  if (!response.ok) {
    let detail: unknown
    try {
      detail = (await response.json()).detail
    } catch {
      detail = undefined
    }
    const message = Array.isArray(detail)
      ? detail.join('; ')
      : typeof detail === 'string'
        ? detail
        : `LotSync API returned ${response.status} for ${path}`
    throw new ApiError(message, response.status)
  }

  return (await response.json()) as T
}
