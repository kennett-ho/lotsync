import { apiGet, apiPostForm } from './client'
import type {
  IngestionValidationDTO, PendingIdentityDTO, SyncRunBatchDTO, SyncSummaryDTO,
} from './types'

/** Field names must match api/routers/inventory_sync.py's form fields exactly. */
export interface InventorySyncFiles {
  tekion_unsold?: File
  tekion_sold?: File
  keyper?: File
  mdd?: File
  recovr?: File
  rapidrecon?: File
}

function reportFormData(files: InventorySyncFiles): FormData {
  const formData = new FormData()
  for (const [field, file] of Object.entries(files)) {
    if (file) formData.append(field, file)
  }
  return formData
}

/**
 * Sprint 10 (Rail D) -- the pre-sync preview. Classifies and validates
 * the selected reports server-side with zero operational mutation;
 * the result drives the preview cards and carries the fingerprint a
 * subsequent run must echo back when acknowledging warnings.
 */
export function validateInventoryReports(files: InventorySyncFiles): Promise<IngestionValidationDTO> {
  return apiPostForm<IngestionValidationDTO>('/inventory-sync/validate', reportFormData(files))
}

/**
 * Sprint 10: the run endpoint revalidates everything itself -- these
 * two extra fields only matter when the (re)validation finds
 * warnings: acknowledgeWarnings asserts a human reviewed them, and
 * validationFingerprint proves the review was of these exact bytes
 * (the server rejects a mismatch as STALE_VALIDATION). The UI never
 * pre-checks the acknowledgement -- see InventorySync.tsx.
 */
export function runInventorySync(
  files: InventorySyncFiles,
  options?: { acknowledgeWarnings?: boolean; validationFingerprint?: string },
): Promise<SyncSummaryDTO> {
  const formData = reportFormData(files)
  if (options?.acknowledgeWarnings) {
    formData.append('acknowledge_warnings', 'true')
    if (options.validationFingerprint) {
      formData.append('validation_fingerprint', options.validationFingerprint)
    }
  }
  return apiPostForm<SyncSummaryDTO>('/inventory-sync/run', formData)
}

export function getSyncHistory(): Promise<SyncRunBatchDTO[]> {
  return apiGet<SyncRunBatchDTO[]>('/inventory-sync/history')
}

export function getExceptions(): Promise<PendingIdentityDTO[]> {
  return apiGet<PendingIdentityDTO[]>('/inventory-sync/exceptions')
}
