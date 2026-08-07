// Display-only cleanup for Recommendation.detail free text, mirroring
// eventDisplay.ts/taskDisplay.ts's philosophy. Only one rule_source
// exists today (key_out_aging -- see sync/reconciler.py's
// generate_key_out_aging_recommendations), whose detail text starts
// with "Tekion stock <X>, " -- already shown as its own badge next to
// the vehicle wherever a Recommendation renders, so stripping it here
// avoids exactly the "duplicated source name / repeated stock number"
// pattern the rest of this pass removes everywhere else.

import type { RecommendationDTO } from './api/types'

export function describeRecommendationDetail(rec: RecommendationDTO): string | null {
  if (!rec.detail) return null
  return rec.detail.replace(/^Tekion stock \S+,\s*/i, '')
}
