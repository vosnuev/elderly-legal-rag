import {
  useMemo,
} from 'react'
import {
  ArrowRight,
  CheckCircle2,
  FileText,
  GitBranch,
} from 'lucide-react'
import { Link } from 'react-router'

import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { PageHeader } from '@/components/workspace/page-header'
import { cn } from '@/lib/utils'
import {
  groupReviewCandidatesByJob,
  type ReviewCandidateJobGroup,
} from '@/features/review/review-candidates'
import { useRagWorkspace } from '@/features/workspace/use-rag-workspace'

export function ReviewQueuePage() {
  const {
    pendingReviewCount,
    reviewCandidates,
  } = useRagWorkspace()
  const reviewJobs = useMemo(
    () => groupReviewCandidatesByJob(reviewCandidates),
    [reviewCandidates],
  )

  return (
    <div className="grid gap-5">
      <PageHeader
        title="Review Queue"
        description="Select a pending document to open its approve and deny workflow."
        action={<Badge variant="outline">{pendingReviewCount} pending candidates</Badge>}
      />

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
        <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
          {reviewJobs.map((group) => (
            <ReviewJobLink key={group.jobId} group={group} />
          ))}
        </div>
      )}
    </div>
  )
}

function ReviewJobLink({
  group,
}: {
  group: ReviewCandidateJobGroup
}) {
  return (
    <Link
      to={`/review-queue/${encodeURIComponent(group.jobId)}`}
      className={cn(
        'block rounded-xl outline-none transition-colors',
        'focus-visible:ring-3 focus-visible:ring-ring/50',
      )}
    >
      <Card className="h-full transition-colors hover:bg-muted/30">
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-3">
              <div className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-md border bg-background">
                <FileText className="size-4 text-muted-foreground" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <CardTitle className="truncate">{group.documentLabel}</CardTitle>
                <CardDescription className="mt-1 truncate">
                  {group.fileName ?? group.jobId}
                </CardDescription>
              </div>
            </div>
            <Badge variant="secondary" className="shrink-0">
              {group.candidates.length}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="grid gap-2">
          <div className="flex min-w-0 items-center gap-2 rounded-md border bg-muted/30 px-3 py-2">
            <GitBranch className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <div className="min-w-0">
              <p className="text-xs text-muted-foreground">Ingest job</p>
              <p className="truncate text-sm font-medium">{group.jobId}</p>
            </div>
          </div>
        </CardContent>
        <CardFooter className="justify-between gap-3">
          <span className="text-xs text-muted-foreground">
            {group.candidates.length} edge candidates pending
          </span>
          <span className="inline-flex items-center gap-1 text-sm font-medium">
            Review
            <ArrowRight className="size-4" aria-hidden="true" />
          </span>
        </CardFooter>
      </Card>
    </Link>
  )
}
