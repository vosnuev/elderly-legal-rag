import { useMemo } from 'react'
import { CheckCircle2 } from 'lucide-react'

import { PageHeader } from '@/components/workspace/page-header'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
} from '@/components/ui/card'
import { ReviewCandidateCard } from '@/features/review/review-candidate-card'
import { groupReviewCandidatesByDocument } from '@/features/review/review-candidates'
import { useRagWorkspace } from '@/features/workspace/use-rag-workspace'

export function ReviewQueuePage() {
  const {
    pendingReviewCount,
    review,
    reviewCandidates,
    status,
    submitReviewDecisionForCandidate,
  } = useRagWorkspace()
  const groupedCandidates = useMemo(
    () => groupReviewCandidatesByDocument(reviewCandidates),
    [reviewCandidates],
  )

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        title="Review Queue"
        description="Review chunk-to-candidate-to-chunk connections with notes, then approve or deny them."
        action={
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{pendingReviewCount} queued</Badge>
            {review?.elapsed_ms !== undefined ? (
              <Badge variant="secondary">{review.elapsed_ms}ms</Badge>
            ) : null}
          </div>
        }
      />

      {groupedCandidates.length === 0 ? (
        <Card>
          <CardContent className="flex min-h-64 items-center justify-center">
            <div className="text-center">
              <CheckCircle2 className="mx-auto size-7 text-muted-foreground" aria-hidden="true" />
              <p className="mt-3 text-sm font-medium">
                {pendingReviewCount > 0
                  ? 'Candidate rows could not be normalized'
                  : 'No pending connection candidates'}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                Start graph add from a staged document to populate this queue.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-6">
          {groupedCandidates.map((group) => (
            <section key={group.documentKey} className="flex flex-col gap-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold">{group.documentLabel}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Connection candidates generated from this document.
                  </p>
                </div>
                <Badge variant="outline">{group.candidates.length} candidates</Badge>
              </div>
              <div className="grid gap-3">
                {group.candidates.map((candidate) => (
                  <ReviewCandidateCard
                    key={candidate.id}
                    candidate={candidate}
                    disabled={status === 'loading'}
                    onDecision={submitReviewDecisionForCandidate}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  )
}
