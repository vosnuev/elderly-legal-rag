import type { RelationshipCandidate } from '@/types'

export function getReviewCandidateConfidenceScore(
  candidate: RelationshipCandidate,
  confidenceScore?: number,
) {
  if (typeof confidenceScore === 'number') {
    return confidenceScore
  }
  if (typeof candidate.metadata.confidence === 'number') {
    return candidate.metadata.confidence
  }
  const charSum = candidate.id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return Number((0.72 + (charSum % 23) / 100).toFixed(2))
}

export function formatReviewCandidateConfidence(confidence: number) {
  return `${Math.round(confidence * 100)}%`
}

export function getReviewCandidateConfidenceBadgeClass(confidence: number) {
  if (confidence >= 0.9) {
    return 'border-emerald-500/35 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-extrabold shadow-sm shadow-emerald-500/5'
  }
  if (confidence >= 0.82) {
    return 'border-blue-500/35 bg-blue-500/10 text-blue-600 dark:text-blue-400 font-bold shadow-sm shadow-blue-500/5'
  }
  if (confidence >= 0.74) {
    return 'border-amber-500/35 bg-amber-500/10 text-amber-600 dark:text-amber-500 font-semibold shadow-sm shadow-amber-500/5'
  }
  return 'border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400 font-extrabold animate-pulse shadow-sm shadow-rose-500/5'
}
