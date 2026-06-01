import {
  useState,
} from 'react'
import { CheckCircle2 } from 'lucide-react'

import { Accordion } from '@/components/ui/accordion'
import {
  Card,
  CardContent,
} from '@/components/ui/card'
import { ReviewCandidateCard } from '@/features/review/review-candidate-card'
import { useRagWorkspace } from '@/features/workspace/use-rag-workspace'

export function ReviewQueuePage() {
  const {
    pendingReviewCount,
    reviewCandidates,
    status,
    submitReviewDecisionForCandidate,
  } = useRagWorkspace()
  const [openCandidate, setOpenCandidate] = useState<string | undefined>()
  const firstCandidateValue = reviewCandidates[0]
    ? getAccordionValue(reviewCandidates[0].id)
    : ''
  const currentCandidateExists = openCandidate
    ? reviewCandidates.some((candidate) => getAccordionValue(candidate.id) === openCandidate)
    : false
  const accordionValue = openCandidate === undefined
    ? firstCandidateValue
    : openCandidate === ''
      ? ''
      : currentCandidateExists
        ? openCandidate
        : firstCandidateValue

  return (
    <div className="grid gap-3">
      {reviewCandidates.length === 0 ? (
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
        <Accordion
          type="single"
          collapsible
          value={accordionValue}
          onValueChange={setOpenCandidate}
          className="grid gap-3"
        >
          {reviewCandidates.map((candidate) => (
            <ReviewCandidateCard
              key={candidate.id}
              accordionValue={getAccordionValue(candidate.id)}
              candidate={candidate}
              disabled={status === 'loading'}
              onDecision={submitReviewDecisionForCandidate}
              onRequestCollapse={() => setOpenCandidate('')}
            />
          ))}
        </Accordion>
      )}
    </div>
  )
}

function getAccordionValue(candidateId: string) {
  return `candidate-${candidateId}`
}
