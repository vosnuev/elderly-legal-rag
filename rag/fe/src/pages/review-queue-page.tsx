import {
  useEffect,
  useMemo,
  useState,
} from 'react'
import {
  ArrowRight,
  Archive,
  CheckCircle2,
  FileText,
  GitBranch,
  ListChecks,
} from 'lucide-react'
import { Link } from 'react-router'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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
import type {
  FileIngestStatusResponse,
  RagDocument,
  RelationshipCandidate,
  ReviewCandidateStatusFilter,
} from '@/types'

const REVIEW_QUEUE_FILTERS = [
  { label: 'Pending', value: 'pending' },
  { label: 'Finished', value: 'finished' },
  { label: 'Both', value: 'all' },
] satisfies Array<{ label: string; value: ReviewCandidateStatusFilter }>

export function ReviewQueuePage() {
  const {
    documents,
    jobs,
    pendingReviewCount,
    refresh,
    reviewCandidates,
  } = useRagWorkspace()
  const [statusFilter, setStatusFilter] = useState<ReviewCandidateStatusFilter>('pending')
  const filteredReviewCandidates = useMemo(
    () => filterReviewCandidatesByStatus(reviewCandidates, statusFilter),
    [reviewCandidates, statusFilter],
  )
  const reviewJobs = useMemo(
    () => groupReviewCandidatesByJob(filteredReviewCandidates),
    [filteredReviewCandidates],
  )
  const reviewCounts = useMemo(
    () => getReviewCandidateCounts(reviewCandidates),
    [reviewCandidates],
  )

  useEffect(() => {
    if (pendingReviewCount === 0) {
      return
    }

    const interval = window.setInterval(() => {
      void refresh({ silent: true })
    }, 3000)
    return () => window.clearInterval(interval)
  }, [pendingReviewCount, refresh])

  return (
    <div className="grid gap-5">
      <PageHeader
        title="Review Queue"
        description="Open pending review work or inspect finished candidate decisions."
        action={<Badge variant="outline">{pendingReviewCount} pending candidates</Badge>}
      />

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-primary/10 bg-card/55 p-3 shadow-sm">
        <div className="flex min-w-0 items-center gap-2">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-primary/15 bg-primary/8 text-primary">
            <ListChecks className="size-4" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-extrabold text-foreground">Candidate review scope</p>
            <p className="text-[10px] font-semibold text-muted-foreground">
              Pending은 편집 가능하고 finished는 read-only로 열립니다.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-border/45 bg-background/60 p-1">
          {REVIEW_QUEUE_FILTERS.map((filter) => (
            <Button
              key={filter.value}
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setStatusFilter(filter.value)}
              className={cn(
                'h-7 rounded-lg px-2.5 text-[10px] font-black uppercase tracking-wider',
                statusFilter === filter.value
                  ? 'bg-primary text-primary-foreground shadow-sm hover:bg-primary/95 hover:text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted/55 hover:text-foreground',
              )}
            >
              {filter.label}
              <span className="ml-1.5 rounded-full bg-background/80 px-1.5 py-0 text-[9px] text-foreground">
                {filter.value === 'pending'
                  ? reviewCounts.pending
                  : filter.value === 'finished'
                    ? reviewCounts.finished
                    : reviewCounts.total}
              </span>
            </Button>
          ))}
        </div>
      </div>

      {filteredReviewCandidates.length === 0 ? (
        <Card>
          <CardContent className="flex min-h-64 items-center justify-center">
            <div className="text-center">
              {statusFilter === 'finished' ? (
                <Archive className="mx-auto size-7 text-muted-foreground" aria-hidden="true" />
              ) : (
                <CheckCircle2 className="mx-auto size-7 text-muted-foreground" aria-hidden="true" />
              )}
              <p className="mt-3 text-sm font-medium">
                {emptyReviewQueueTitle(statusFilter, pendingReviewCount)}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {emptyReviewQueueDescription(statusFilter)}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
          {reviewJobs.map((group) => (
            <ReviewJobLink
              key={group.jobId}
              documents={documents}
              group={group}
              jobs={jobs}
              statusFilter={statusFilter}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function ReviewJobLink({
  documents,
  group,
  jobs,
  statusFilter,
}: {
  documents: RagDocument[]
  group: ReviewCandidateJobGroup
  jobs: FileIngestStatusResponse[]
  statusFilter: ReviewCandidateStatusFilter
}) {
  const documentInfo = getReviewJobDocumentInfo(group, documents, jobs)
  const counts = getReviewCandidateCounts(group.candidates)
  const modeLabel = statusFilter === 'finished'
    ? 'Inspect'
    : statusFilter === 'all'
      ? 'Open'
      : 'Review'

  return (
    <Link
      to={`/review-queue/${encodeURIComponent(group.jobId)}?view=${statusFilter}`}
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
                <CardTitle className="truncate">{documentInfo.title}</CardTitle>
                <CardDescription className="mt-1 truncate">
                  {documentInfo.subtitle}
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
            {counts.pending > 0
              ? `${counts.pending} pending · ${counts.finished} finished`
              : `${counts.finished} finished decisions`}
          </span>
          <span className="inline-flex items-center gap-1 text-sm font-medium">
            {modeLabel}
            <ArrowRight className="size-4" aria-hidden="true" />
          </span>
        </CardFooter>
      </Card>
    </Link>
  )
}

function filterReviewCandidatesByStatus(
  candidates: RelationshipCandidate[],
  statusFilter: ReviewCandidateStatusFilter,
) {
  if (statusFilter === 'all') {
    return candidates
  }
  if (statusFilter === 'finished') {
    return candidates.filter((candidate) => !isPendingReviewCandidate(candidate))
  }
  return candidates.filter(isPendingReviewCandidate)
}

function getReviewCandidateCounts(candidates: RelationshipCandidate[]) {
  const pending = candidates.filter(isPendingReviewCandidate).length
  return {
    finished: Math.max(candidates.length - pending, 0),
    pending,
    total: candidates.length,
  }
}

function isPendingReviewCandidate(candidate: RelationshipCandidate) {
  return candidate.status.toLowerCase() === 'pending_review'
}

function emptyReviewQueueTitle(
  statusFilter: ReviewCandidateStatusFilter,
  pendingReviewCount: number,
) {
  if (statusFilter === 'finished') {
    return 'No finished review decisions'
  }
  if (pendingReviewCount > 0) {
    return 'Candidate rows could not be normalized'
  }
  return 'No pending connection candidates'
}

function emptyReviewQueueDescription(statusFilter: ReviewCandidateStatusFilter) {
  if (statusFilter === 'finished') {
    return 'Finished approvals and denials will appear here after a review job is committed.'
  }
  if (statusFilter === 'all') {
    return 'Start graph add from a staged document, then commit review decisions to populate this view.'
  }
  return 'Start graph add from a staged document to populate this queue.'
}

function getReviewJobDocumentInfo(
  group: ReviewCandidateJobGroup,
  documents: RagDocument[],
  jobs: FileIngestStatusResponse[],
) {
  const matchedJob = jobs.find((job) => job.job_id === group.jobId) ?? null
  const firstCandidate = group.candidates[0] ?? null
  const candidateDocumentId = firstCandidate
    ? getMetadataString(firstCandidate, ['document_id'])
    : null
  const candidateDocumentTitle = displayText(
    firstCandidate
      ? getMetadataString(firstCandidate, ['document_title', 'source_title', 'title'])
      : null,
    { skipUuid: true },
  )
  const candidateFileName = displayText(
    firstCandidate ? getMetadataString(firstCandidate, ['file_name']) : null,
  )
  const matchedJobFileName = displayText(matchedJob?.file_name)

  const matchedDocument = documents.find((document) => (
    (candidateDocumentId && document.document_id === candidateDocumentId) ||
    (matchedJob?.document_id && document.location === matchedJob.document_id) ||
    document.job_id === group.jobId ||
    (matchedJobFileName && document.file_name === matchedJobFileName) ||
    (candidateFileName && document.file_name === candidateFileName) ||
    (candidateDocumentTitle && (
      document.source_title === candidateDocumentTitle ||
      document.file_name === candidateDocumentTitle
    )) ||
    document.source_title === group.documentLabel ||
    document.file_name === group.documentLabel
  )) ?? null

  const title = documentTitleFrom(
    matchedDocument?.source_title,
    candidateDocumentTitle ??
      matchedJobFileName ??
      matchedDocument?.file_name ??
      candidateFileName ??
      group.fileName ??
      (group.documentLabel !== group.jobId ? group.documentLabel : null),
  )
  const subtitleCandidate =
    displayText(matchedDocument?.file_name) ??
    matchedJobFileName ??
    candidateFileName ??
    displayText(group.fileName)
  const subtitle =
    subtitleCandidate && subtitleCandidate !== title
      ? subtitleCandidate
      : `${group.candidates.length} edge candidates pending`

  return {
    subtitle,
    title,
  }
}

function getMetadataString(candidate: RelationshipCandidate, keys: string[]) {
  for (const key of keys) {
    const value = candidate.metadata[key]
    if (typeof value === 'string' && value.trim()) {
      return value
    }
    if (typeof value === 'number' || typeof value === 'boolean') {
      return String(value)
    }
  }

  return null
}

function documentTitleFrom(...values: Array<string | null | undefined>) {
  const value = firstDisplayValue(values, { skipUuid: true }) ?? 'Review document'
  return stripKnownExtension(value)
}

function firstDisplayValue(
  values: Array<string | null | undefined>,
  options: { skipUuid?: boolean } = {},
) {
  for (const value of values) {
    const normalized = displayText(value, options)
    if (normalized) {
      return normalized
    }
  }

  return null
}

function displayText(
  value: string | null | undefined,
  options: { skipUuid?: boolean } = {},
) {
  const trimmed = value?.trim()
  if (!trimmed || trimmed.toLowerCase() === 'unknown') {
    return null
  }

  const normalized = (trimmed.split('/').pop() || trimmed).normalize('NFC')
  if (options.skipUuid && isUuidLike(normalized)) {
    return null
  }

  return normalized
}

function stripKnownExtension(value: string) {
  return value.replace(/\.(toon|md|markdown|txt|json|pdf|docx?)$/i, '')
}

function isUuidLike(value: string) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
}
