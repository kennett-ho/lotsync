import { apiGet } from './client'
import type { ActivityDTO } from './types'

export interface ActivityFilters {
  [key: string]: string | number | undefined
  vin?: string
  limit?: number
}

export function getActivity(filters?: ActivityFilters): Promise<ActivityDTO[]> {
  return apiGet<ActivityDTO[]>('/activity', filters)
}
