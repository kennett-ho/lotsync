import { apiGet } from './client'
import type { RecommendationDTO } from './types'

export interface RecommendationFilters {
  [key: string]: string | undefined
  status?: string
}

export function getRecommendations(filters?: RecommendationFilters): Promise<RecommendationDTO[]> {
  return apiGet<RecommendationDTO[]>('/recommendations', filters)
}
