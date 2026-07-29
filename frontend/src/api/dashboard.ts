import { apiGet } from './client'
import type { DashboardSummaryDTO } from './types'

export function getDashboard(): Promise<DashboardSummaryDTO> {
  return apiGet<DashboardSummaryDTO>('/dashboard')
}
