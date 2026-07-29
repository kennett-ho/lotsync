import { apiGet } from './client'
import type { VehicleDTO, VehicleDetailDTO } from './types'

export function getVehicles(): Promise<VehicleDTO[]> {
  return apiGet<VehicleDTO[]>('/vehicles')
}

export function getVehicleDetail(vin: string): Promise<VehicleDetailDTO> {
  return apiGet<VehicleDetailDTO>(`/vehicles/${encodeURIComponent(vin)}`)
}
