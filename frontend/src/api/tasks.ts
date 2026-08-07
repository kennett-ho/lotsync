import { apiGet, apiGetBlob } from './client'
import type { TaskDTO } from './types'

export interface TaskFilters {
  [key: string]: string | undefined
  department?: string
  priority?: string
  commitment_standing?: string
  assigned_employee_id?: string
}

export function getTasks(filters?: TaskFilters): Promise<TaskDTO[]> {
  return apiGet<TaskDTO[]>('/tasks', filters)
}

/** GET /tasks/work-order -- the printable Daily Work Order PDF. */
export function getWorkOrderPdf(): Promise<{ blob: Blob; filename: string }> {
  return apiGetBlob('/tasks/work-order')
}
