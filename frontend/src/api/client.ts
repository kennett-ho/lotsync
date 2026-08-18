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

import { currentAccessToken } from '../auth/supabase'

const DEFAULT_API_BASE_URL = 'http://localhost:8000'

/**
 * Sprint 05 -- the auth header this file's own docstring reserved a
 * seat for. Resolves to a Bearer header when a Supabase session
 * exists, {} otherwise (auth disabled, or signed out) -- so every
 * request shape below is unchanged except for this one merge point.
 */
async function authHeaders(): Promise<Record<string, string>> {
  const token = await currentAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// Overridable via a .env.local VITE_API_BASE_URL, same convention the
// backend already uses for LOTSYNC_* env vars -- not committed, since
// frontend/.gitignore already excludes .env* files project-wide.
export const API_BASE_URL: string =
  (import.meta as unknown as { env?: Record<string, string | undefined> }).env
    ?.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL

export class ApiError extends Error {
  readonly status: number
  // Sprint 11: the server-generated X-Request-ID from the failed
  // response ('' when unreachable). Lets the UI show a safe support
  // reference that matches the backend's structured log record --
  // never a traceback or internal detail.
  readonly requestId: string

  constructor(message: string, status: number, requestId = '') {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.requestId = requestId
  }
}

function requestIdOf(response: Response): string {
  return response.headers.get('X-Request-ID') ?? ''
}

/**
 * Sprint 10 (Rail D) -- a structured rejection from the ingestion
 * boundary. POST /inventory-sync/run and /validate reject with
 * detail: { code, validation } (see api/routers/inventory_sync.py's
 * _reject); the validation payload is a full IngestionValidationDTO
 * the screen renders as the preview, so the user sees exactly WHY the
 * server said no -- never a flattened string. `code` is one of
 * REPORT_VALIDATION_FAILED (422), WARNINGS_NOT_ACKNOWLEDGED (409), or
 * STALE_VALIDATION (409).
 */
export class ValidationRejectedError extends ApiError {
  readonly code: string
  // Typed as unknown here (transport layer); inventorySync.ts narrows
  // it to IngestionValidationDTO at its own boundary.
  readonly validation: unknown

  constructor(code: string, validation: unknown, status: number, requestId = '') {
    super(`Report validation rejected (${code})`, status, requestId)
    this.name = 'ValidationRejectedError'
    this.code = code
    this.validation = validation
  }
}

/**
 * Sprint 09 -- session-lifecycle signal (Phase 18): a 401 from the
 * backend means the token is missing/expired/invalid BEYOND what
 * supabase-js could silently refresh -- AuthGate listens and returns
 * the user to a clean login rather than leaving dead screens. 403 is
 * deliberately NOT globally handled here: authenticated-but-not-
 * allowed is a per-action condition (e.g. lot staff hitting a
 * manager-only action) that each screen surfaces in place; only
 * AccessProvider's own /me probe treats a 403 as "this account has no
 * access at all" (disabled/offboarded) and shows the dedicated
 * screen.
 */
export const AUTH_EXPIRED_EVENT = 'dealerdoh:auth-expired'

function signalStatus(status: number) {
  if (status === 401) {
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
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
    response = await fetch(url.toString(), { headers: await authHeaders() })
  } catch {
    throw new ApiError(
      `Could not reach the LotSync API at ${API_BASE_URL}. Is the backend running?`,
      0,
    )
  }

  if (response.status === 404) {
    throw new ApiError('Not found', 404, requestIdOf(response))
  }
  if (!response.ok) {
    signalStatus(response.status)
    throw new ApiError(`LotSync API returned ${response.status} for ${path}`, response.status, requestIdOf(response))
  }

  return (await response.json()) as T
}

/**
 * Sprint 09 -- JSON POST for the user-administration endpoints. Same
 * transport-only philosophy as apiGet; FastAPI's HTTPException detail
 * (always a plain, user-appropriate sentence on these routes) becomes
 * the ApiError message so screens can show it directly.
 */
export async function apiPostJson<T>(path: string, body: unknown): Promise<T> {
  const url = new URL(path, API_BASE_URL)

  let response: Response
  try {
    response = await fetch(url.toString(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
      body: JSON.stringify(body ?? {}),
    })
  } catch {
    throw new ApiError(
      `Could not reach the LotSync API at ${API_BASE_URL}. Is the backend running?`,
      0,
    )
  }

  if (!response.ok) {
    signalStatus(response.status)
    let detail: unknown
    try {
      detail = (await response.json()).detail
    } catch {
      detail = undefined
    }
    const message = typeof detail === 'string'
      ? detail
      : `LotSync API returned ${response.status} for ${path}`
    throw new ApiError(message, response.status, requestIdOf(response))
  }

  return (await response.json()) as T
}

/**
 * For endpoints that hand back a file rather than JSON -- currently
 * only GET /tasks/work-order's PDF. Same reachability/status handling
 * as apiGet, but resolves the raw Blob plus whatever filename the
 * server's Content-Disposition suggests, since the caller needs both
 * to trigger a browser download.
 */
export async function apiGetBlob(path: string): Promise<{ blob: Blob; filename: string }> {
  const url = new URL(path, API_BASE_URL)

  let response: Response
  try {
    response = await fetch(url.toString(), { headers: await authHeaders() })
  } catch {
    throw new ApiError(
      `Could not reach the LotSync API at ${API_BASE_URL}. Is the backend running?`,
      0,
    )
  }

  if (!response.ok) {
    signalStatus(response.status)
    throw new ApiError(`LotSync API returned ${response.status} for ${path}`, response.status, requestIdOf(response))
  }

  const disposition = response.headers.get('Content-Disposition') ?? ''
  const filename = disposition.match(/filename="?([^"]+)"?/)?.[1] ?? 'download'

  return { blob: await response.blob(), filename }
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
    response = await fetch(url.toString(), {
      method: 'POST',
      body: formData,
      headers: await authHeaders(),
    })
  } catch {
    throw new ApiError(
      `Could not reach the LotSync API at ${API_BASE_URL}. Is the backend running?`,
      0,
    )
  }

  if (!response.ok) {
    signalStatus(response.status)
    let detail: unknown
    try {
      detail = (await response.json()).detail
    } catch {
      detail = undefined
    }
    // Sprint 10: the ingestion boundary rejects with a structured
    // { code, validation } object -- surface it as its own error type
    // so the Inventory Sync screen can render the full preview instead
    // of a flattened sentence.
    if (detail && typeof detail === 'object' && !Array.isArray(detail)
        && 'code' in detail && 'validation' in detail) {
      const d = detail as { code: string; validation: unknown }
      throw new ValidationRejectedError(d.code, d.validation, response.status, requestIdOf(response))
    }
    const message = Array.isArray(detail)
      ? detail.join('; ')
      : typeof detail === 'string'
        ? detail
        : typeof detail === 'object' && detail !== null && 'message' in detail
          && typeof (detail as { message: unknown }).message === 'string'
          ? (detail as { message: string }).message
          : `LotSync API returned ${response.status} for ${path}`
    throw new ApiError(message, response.status, requestIdOf(response))
  }

  return (await response.json()) as T
}
