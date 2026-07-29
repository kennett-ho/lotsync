import { apiGet } from './client'
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
