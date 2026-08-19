import { apiGet } from './client'
import type { VehicleDTO, VehicleDetailDTO } from './types'

/**
 * Default: active inventory only (the server excludes Tekion-sold
 * rows). includeSold widens to the full roster -- Sprint 12's Sold
 * filter uses it; sold rows are identified by tekion_status ===
 * 'Sold' (see queries/vehicles.py).
 */
export function getVehicles(options?: { includeSold?: boolean }): Promise<VehicleDTO[]> {
  return apiGet<VehicleDTO[]>(options?.includeSold ? '/vehicles?include_sold=true' : '/vehicles')
}

export function getVehicleDetail(vin: string): Promise<VehicleDetailDTO> {
  return apiGet<VehicleDetailDTO>(`/vehicles/${encodeURIComponent(vin)}`)
}
