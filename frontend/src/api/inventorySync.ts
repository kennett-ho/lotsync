import { apiGet, apiPostForm } from './client'
import type { PendingIdentityDTO, SyncRunBatchDTO, SyncSummaryDTO } from './types'

/** Field names must match api/routers/inventory_sync.py's run_sync() form fields exactly. */
export interface InventorySyncFiles {
  tekion_unsold?: File
  tekion_sold?: File
  keyper?: File
  mdd?: File
  recovr?: File
  rapidrecon?: File
}

export function runInventorySync(files: InventorySyncFiles): Promise<SyncSummaryDTO> {
  const formData = new FormData()
  for (const [field, file] of Object.entries(files)) {
    if (file) formData.append(field, file)
  }
  return apiPostForm<SyncSummaryDTO>('/inventory-sync/run', formData)
}

export function getSyncHistory(): Promise<SyncRunBatchDTO[]> {
  return apiGet<SyncRunBatchDTO[]>('/inventory-sync/history')
}

export function getExceptions(): Promise<PendingIdentityDTO[]> {
  return apiGet<PendingIdentityDTO[]>('/inventory-sync/exceptions')
}
