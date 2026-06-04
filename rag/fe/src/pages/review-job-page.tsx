import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'
import {
  ArrowLeft,
  AlertTriangle,
  CheckCircle2,
  CheckIcon,
  ChevronLeft,
  ChevronRight,
  Network,
  XIcon,
  ArrowUpDown,
  Layers,
  SlidersHorizontal,
} from 'lucide-react'
import {
  useNavigate,
  useParams,
  useSearchParams,
} from 'react-router'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { PageHeader } from '@/components/workspace/page-header'
import {
  ReviewCandidateDetailPanel,
  ReviewCandidateListItem,
} from '@/features/review/review-candidate-card'
import { getReviewCandidateConfidenceScore } from '@/features/review/review-candidate-utils'
import {
  groupReviewCandidatesByJob,
  normalizeReviewCandidates,
} from '@/features/review/review-candidates'
import { useRagWorkspace } from '@/features/workspace/use-rag-workspace'
import { cn } from '@/lib/utils'
import { listReviewCandidates } from '@/api/rag'
import type {
  RagDocument,
  RelationshipCandidate,
  ReviewCandidateStatusFilter,
} from '@/types'

type ReviewDecisionAction = 'yes' | 'no'

type DraftReviewDecision = {
  action: ReviewDecisionAction
  note: string | null
}

type CandidateAnnotation = {
  note: string
  editedRationale: string
}

type CandidateSortMode = 'default' | 'confidence_desc' | 'confidence_asc'

type JobScopedCandidateState = {
  candidates: RelationshipCandidate[]
  jobId: string
}

export function ReviewJobPage() {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const reviewStatusFilter = readReviewStatusFilter(searchParams.get('view'))
  const {
    jobs,
    reviewCandidates,
    refresh,
    status,
    submitReviewDecisionsForJob,
    documents,
  } = useRagWorkspace()

  // Parent states for Bulk Action controller
  const [checkedIds, setCheckedIds] = useState<Record<string, boolean>>({})
  const [draftDecisions, setDraftDecisions] = useState<Record<string, DraftReviewDecision>>({})
  const [isCommitting, setIsCommitting] = useState(false)
  const [committedJobIds, setCommittedJobIds] = useState<Set<string>>(() => new Set())
  const [exitDialogOpen, setExitDialogOpen] = useState(false)
  const [exitDialogIntent, setExitDialogIntent] = useState<'back' | 'abort'>('back')
  const [activeCandidateId, setActiveCandidateId] = useState<string | null>(null)
  const [candidateAnnotations, setCandidateAnnotations] = useState<Record<string, CandidateAnnotation>>({})
  const [candidatePage, setCandidatePage] = useState(1)
  const [candidatePageSize, setCandidatePageSize] = useState(10)
  const [candidateSortMode, setCandidateSortMode] = useState<CandidateSortMode>('default')
  const [isFilterExpanded, setIsFilterExpanded] = useState(false)
  const [jobScopedCandidateState, setJobScopedCandidateState] =
    useState<JobScopedCandidateState | null>(null)

  const loadJobScopedCandidates = useCallback(async () => {
    if (!jobId) {
      return []
    }

    const response = await listReviewCandidates('all', { jobId })
    return normalizeReviewCandidates(response)
  }, [jobId])

  useEffect(() => {
    let cancelled = false

    void loadJobScopedCandidates()
      .then((candidates) => {
        if (!cancelled) {
          setJobScopedCandidateState({ candidates, jobId })
        }
      })
      .catch((error) => {
        console.error('Failed to load review candidates for job.', error)
        if (!cancelled) {
          setJobScopedCandidateState({ candidates: [], jobId })
        }
      })

    return () => {
      cancelled = true
    }
  }, [jobId, loadJobScopedCandidates])

  const jobScopedCandidates = jobScopedCandidateState?.jobId === jobId
    ? jobScopedCandidateState.candidates
    : null
  const candidateSource = jobScopedCandidates ?? reviewCandidates
  const reviewJobs = useMemo(
    () => groupReviewCandidatesByJob(candidateSource),
    [candidateSource],
  )
  const selectedJob = useMemo(
    () => reviewJobs.find((group) => group.jobId === jobId) ?? null,
    [jobId, reviewJobs],
  )
  const selectedCandidates = useMemo(
    () => filterReviewCandidatesByStatus(selectedJob?.candidates ?? [], reviewStatusFilter),
    [reviewStatusFilter, selectedJob],
  )
  const actionableCandidates = useMemo(
    () => selectedCandidates.filter(isPendingReviewCandidate),
    [selectedCandidates],
  )
  const sortedCandidates = useMemo(
    () => sortReviewCandidates(selectedCandidates, candidateSortMode),
    [candidateSortMode, selectedCandidates],
  )
  const candidatePageCount = Math.max(1, Math.ceil(sortedCandidates.length / candidatePageSize))
  const effectiveCandidatePage = Math.min(candidatePage, candidatePageCount)
  const candidatePageStart = sortedCandidates.length === 0
    ? 0
    : (effectiveCandidatePage - 1) * candidatePageSize
  const candidatePageEnd = Math.min(candidatePageStart + candidatePageSize, sortedCandidates.length)
  const paginatedCandidates = useMemo(
    () => sortedCandidates.slice(candidatePageStart, candidatePageEnd),
    [candidatePageEnd, candidatePageStart, sortedCandidates],
  )
  const selectedCandidateIds = useMemo(
    () => new Set(selectedCandidates.map((candidate) => candidate.id)),
    [selectedCandidates],
  )
  const actionableCandidateIds = useMemo(
    () => new Set(actionableCandidates.map((candidate) => candidate.id)),
    [actionableCandidates],
  )
  const scopedCheckedIds = useMemo(
    () => filterByCandidateIds(checkedIds, actionableCandidateIds),
    [actionableCandidateIds, checkedIds],
  )
  const scopedDraftDecisions = useMemo(
    () => filterByCandidateIds(draftDecisions, actionableCandidateIds),
    [actionableCandidateIds, draftDecisions],
  )
  const commitSubmitted = committedJobIds.has(jobId)
  const selectedJobStatus = useMemo(
    () => jobs.find((job) => job.job_id === selectedJob?.jobId) ?? null,
    [jobs, selectedJob],
  )
  const effectiveActiveCandidateId =
    activeCandidateId && selectedCandidateIds.has(activeCandidateId)
      ? activeCandidateId
      : null
  const activeCandidate = useMemo(
    () => (
      selectedCandidates.find((candidate) => candidate.id === effectiveActiveCandidateId) ??
      null
    ),
    [effectiveActiveCandidateId, selectedCandidates],
  )
  const activeCandidateAnnotation = activeCandidate
    ? candidateAnnotations[activeCandidate.id] ?? {
      note: '',
      editedRationale: activeCandidate.rationale || '',
    }
    : null
  const activeCandidateReadOnly =
    activeCandidate !== null && !isPendingReviewCandidate(activeCandidate)
  const activeCandidateNote = activeCandidateReadOnly
    ? getCandidateReviewNote(activeCandidate)
    : activeCandidateAnnotation?.note ?? ''
  const activeCandidateEditedRationale =
    activeCandidateAnnotation?.editedRationale ?? activeCandidate?.rationale ?? ''

  const selectedDocument = useMemo(() => {
    if (!selectedJob) {
      return null
    }

    const firstCandidate = selectedCandidates[0] ?? selectedJob.candidates[0]
    const candidateDocumentId = firstCandidate
      ? getMetadataString(firstCandidate, ['document_id'])
      : null
    const selectedDocumentId = selectedJobStatus?.document_id ?? candidateDocumentId

    return documents.find((document) => (
      (selectedDocumentId && (
        document.document_id === selectedDocumentId ||
        document.location === selectedDocumentId
      )) ||
      document.job_id === selectedJob.jobId ||
      (selectedJobStatus?.file_name && sameDisplayText(document.file_name, selectedJobStatus.file_name)) ||
      (selectedJob.fileName && sameDisplayText(document.file_name, selectedJob.fileName)) ||
      sameDisplayText(document.source_title, selectedJob.documentLabel) ||
      sameDisplayText(document.file_name, selectedJob.documentLabel)
    )) ?? null
  }, [documents, selectedCandidates, selectedJob, selectedJobStatus])
  const selectedDocumentName =
    documentTitleFrom(
      selectedDocument?.source_title,
      selectedDocument?.file_name,
      selectedJobStatus?.file_name,
      selectedJob?.fileName,
      selectedJob?.documentLabel,
      selectedJob?.jobId,
    )

  // Check state helpers
  const checkedCount = Object.keys(scopedCheckedIds).filter(
    (id) => scopedCheckedIds[id] && actionableCandidateIds.has(id)
  ).length

  const isAllSelected =
    actionableCandidates.length > 0 &&
    actionableCandidates.every((candidate) => scopedCheckedIds[candidate.id])
  const draftDecisionCount = actionableCandidates.filter(
    (candidate) => Boolean(scopedDraftDecisions[candidate.id]),
  ).length
  const remainingDecisionCount = Math.max(actionableCandidates.length - draftDecisionCount, 0)
  const allCandidatesDecided =
    actionableCandidates.length > 0 &&
    remainingDecisionCount === 0
  const hasUncommittedDraft = draftDecisionCount > 0 && !commitSubmitted
  const hasActionableCandidates = actionableCandidates.length > 0
  const reviewCommitStatus = !hasActionableCandidates
    ? 'Read Only'
    : commitSubmitted
      ? 'Submitted'
      : allCandidatesDecided
        ? 'All Decided'
        : `${draftDecisionCount}/${actionableCandidates.length} (${remainingDecisionCount} left)`
  const shouldConfirmExit =
    actionableCandidates.length > 0 &&
    !commitSubmitted &&
    (hasUncommittedDraft || !allCandidatesDecided)
  const reviewControlsDisabled = status === 'loading' || isCommitting || commitSubmitted

  useEffect(() => {
    if (status === 'loading' || selectedCandidates.length === 0 || !hasActionableCandidates) {
      return
    }

    const interval = window.setInterval(() => {
      void refresh({ silent: true })
      void loadJobScopedCandidates()
        .then((candidates) => {
          setJobScopedCandidateState({ candidates, jobId })
        })
        .catch((error) => {
          console.error('Failed to refresh review candidates for job.', error)
        })
    }, 3000)
    return () => window.clearInterval(interval)
  }, [hasActionableCandidates, jobId, loadJobScopedCandidates, refresh, selectedCandidates.length, status])

  useEffect(() => {
    if (!commitSubmitted || reviewStatusFilter !== 'pending') {
      return
    }

    const pendingCount = selectedJobStatus?.pending_review_count
    if (pendingCount === 0 || !hasActionableCandidates) {
      setSearchParams({ view: 'finished' }, { replace: true })
    }
  }, [
    commitSubmitted,
    hasActionableCandidates,
    reviewStatusFilter,
    selectedJobStatus?.pending_review_count,
    setSearchParams,
  ])

  const handleCandidatePageChange = (nextPage: number) => {
    const boundedPage = Math.min(Math.max(nextPage, 1), candidatePageCount)
    setCandidatePage(boundedPage)
    setActiveCandidateId(null)
  }

  const handleCandidatePageSizeChange = (nextPageSize: number) => {
    setCandidatePageSize(nextPageSize)
    setCandidatePage(1)
    setActiveCandidateId(null)
  }

  const handleCandidateSortModeChange = (nextSortMode: CandidateSortMode) => {
    setCandidateSortMode(nextSortMode)
    setCandidatePage(1)
    setActiveCandidateId(null)
  }

  const handleToggleSelectAll = () => {
    if (isAllSelected) {
      setCheckedIds({})
    } else {
      const nextChecked: Record<string, boolean> = {}
      actionableCandidates.forEach((candidate) => {
        nextChecked[candidate.id] = true
      })
      setCheckedIds(nextChecked)
    }
  }

  const handleCheckedChange = (candidateId: string, checked: boolean) => {
    if (!actionableCandidateIds.has(candidateId)) {
      return
    }
    setCheckedIds((prev) => ({
      ...prev,
      [candidateId]: checked,
    }))
  }

  const handleBulkDecision = (action: 'yes' | 'no') => {
    const idsToProcess = Object.keys(scopedCheckedIds).filter(
      (id) => scopedCheckedIds[id] && actionableCandidateIds.has(id)
    )

    if (idsToProcess.length === 0) return

    setDraftDecisions((prev) => {
      const next = { ...prev }
      idsToProcess.forEach((candidateId) => {
        next[candidateId] = {
          action,
          note: prev[candidateId]?.note ?? null,
        }
      })
      return next
    })
    setCheckedIds({})
  }

  const updateCandidateAnnotation = (
    candidateId: string,
    patch: Partial<CandidateAnnotation>,
  ) => {
    const candidate = selectedCandidates.find((item) => item.id === candidateId)
    setCandidateAnnotations((prev) => {
      const current = prev[candidateId] ?? {
        note: '',
        editedRationale: candidate?.rationale ?? '',
      }
      return {
        ...prev,
        [candidateId]: {
          ...current,
          ...patch,
        },
      }
    })
  }

  const handleSingleDecision = (
    candidateId: string,
    action: 'yes' | 'no',
    note: string,
    editedRationale?: string,
  ) => {
    if (!selectedJob) {
      return
    }
    const candidate = selectedCandidates.find((item) => item.id === candidateId)
    if (!candidate || !isPendingReviewCandidate(candidate)) {
      return
    }
    const nextDraftDecisions = {
      ...draftDecisions,
      [candidateId]: {
        action,
        note: buildDecisionNote(
          candidate,
          note,
          editedRationale,
        ),
      },
    }
    setDraftDecisions(nextDraftDecisions)
    setCheckedIds((prev) => ({
      ...prev,
      [candidateId]: false,
    }))
    updateCandidateAnnotation(candidateId, {
      note,
      editedRationale: editedRationale ?? candidate?.rationale ?? '',
    })

    const nextCandidateId = findNextUndecidedCandidateId(
      sortedCandidates,
      candidateId,
      nextDraftDecisions,
    )
    setActiveCandidateId(nextCandidateId)

    const nextPage = getCandidatePageForId(
      sortedCandidates,
      nextCandidateId,
      candidatePageSize,
    )
    if (nextPage !== null) {
      setCandidatePage(nextPage)
    }
  }

  const handleCommitReviewTask = async () => {
    if (!selectedJob || !allCandidatesDecided || isCommitting || commitSubmitted) {
      return
    }

    setIsCommitting(true)
    try {
      const decisions = actionableCandidates.flatMap((candidate) => {
        const decision = scopedDraftDecisions[candidate.id]
        if (!decision) {
          return []
        }
        return [
          {
            candidate_id: candidate.id,
            action: decision.action,
            note: decision.note,
          },
        ]
      })

      if (decisions.length !== actionableCandidates.length) {
        return
      }

      await submitReviewDecisionsForJob(
        selectedJob.jobId,
        decisions,
      )
      setCommittedJobIds((prev) => new Set(prev).add(selectedJob.jobId))
      setCheckedIds({})
      setActiveCandidateId(null)
      await refresh({ silent: true })
      setJobScopedCandidateState({
        candidates: await loadJobScopedCandidates(),
        jobId: selectedJob.jobId,
      })
    } catch (error) {
      console.error('Failed to commit review task:', error)
    } finally {
      setIsCommitting(false)
    }
  }

  const requestExitReview = (intent: 'back' | 'abort') => {
    setExitDialogIntent(intent)
    if (shouldConfirmExit) {
      setExitDialogOpen(true)
      return
    }
    navigate('/review-queue')
  }

  const confirmExitReview = () => {
    setDraftDecisions({})
    setCheckedIds({})
    setExitDialogOpen(false)
    navigate('/review-queue')
  }

  const activeDocumentRefs = useMemo(
    () => activeCandidate
      ? getCandidateDocumentRefs(activeCandidate, documents)
      : { sourceDoc: null, targetDoc: null },
    [activeCandidate, documents],
  )

  if (!selectedJob || selectedCandidates.length === 0) {
    return (
      <div className="grid gap-4">
        <PageHeader
          title="Review Document"
          description="This review job is not currently pending."
          action={<BackToQueueButton onBack={() => navigate('/review-queue')} />}
        />
        <Card className="border border-primary/10 rounded-2xl bg-card/65 backdrop-blur-md">
          <CardContent className="flex min-h-64 items-center justify-center">
            <div className="text-center">
              <CheckCircle2 className="mx-auto size-9 text-chart-3 animate-pulse" aria-hidden="true" />
              <p className="mt-3 text-sm font-extrabold text-foreground">
                {reviewStatusFilter === 'finished'
                  ? 'No finished edge candidates'
                  : 'No pending edge candidates'}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Return to the queue and choose a review document.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 relative pb-6">
      <PageHeader
        title={`Review: ${selectedDocumentName}`}
        description={`${reviewStatusFilter === 'finished' ? 'Read-only review archive' : 'Pipeline review workspace'} · Job: ${selectedJob.jobId}`}
        action={<BackToQueueButton onBack={() => requestExitReview('back')} />}
      />

      {/* Floating Ultra-Slim Bulk Action Bar (Visible when N items are selected) */}
      <div
        className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-full max-w-2xl px-4 transition-all duration-500 ease-out transform ${
          checkedCount > 0
            ? 'opacity-100 translate-y-0 scale-100'
            : 'opacity-0 translate-y-12 scale-95 pointer-events-none'
        }`}
      >
        <div className="flex items-center justify-between gap-4 rounded-xl border border-primary/20 bg-card/85 backdrop-blur-2xl p-3 px-4.5 shadow-2xl shadow-primary/10 animate-neon-glow">
          {/* Header Metric */}
          <div className="flex items-center gap-3">
            <div className="flex size-7.5 items-center justify-center rounded-lg bg-gradient-to-tr from-primary to-accent text-primary-foreground font-black text-xs shadow-md">
              {checkedCount}
            </div>
            <div>
              <p className="text-[10px] font-black text-primary uppercase tracking-widest leading-none">
                Workspace Action
              </p>
              <p className="mt-1 text-[10px] text-muted-foreground font-bold leading-none">
                {checkedCount} selected
              </p>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2.5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setCheckedIds({})}
              disabled={reviewControlsDisabled}
              className="h-8.5 px-3 rounded-lg border-border bg-background/55 text-muted-foreground hover:text-foreground font-bold text-xs transition-all"
            >
              Cancel
            </Button>
            
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void handleBulkDecision('no')}
              disabled={reviewControlsDisabled}
              className="h-8.5 px-3 rounded-lg border-destructive/20 hover:border-destructive bg-destructive/5 hover:bg-destructive/10 text-destructive font-bold transition-all text-xs flex items-center gap-1"
            >
              <XIcon className="size-3.5" />
              Stage Deny
            </Button>
            
            <Button
              type="button"
              size="sm"
              onClick={() => void handleBulkDecision('yes')}
              disabled={reviewControlsDisabled}
              className="h-8.5 px-4.5 rounded-lg bg-gradient-to-r from-chart-3 to-chart-3 hover:from-chart-3/95 hover:to-chart-3/95 text-primary-foreground font-extrabold shadow-md hover:shadow-chart-3/15 transition-all text-xs flex items-center gap-1"
            >
              <CheckIcon className="size-3.5" />
              Stage Approve
            </Button>
          </div>
        </div>
      </div>


      {/* Main review workspace: compact candidate queue on the left, selected detail on the right. */}
      <section className="review-job-candidates flex min-h-0 flex-1 flex-col gap-3.5" aria-labelledby="edge-candidates-title">
        <div className="review-job-candidates-header flex flex-wrap items-center justify-between gap-3 p-0.5">
          <div className="review-job-candidates-heading flex items-center gap-2.5 min-w-0">
            <div className="review-job-candidates-icon flex size-8.5 shrink-0 items-center justify-center rounded-lg bg-accent/10 text-accent border border-accent/15" aria-hidden="true">
              <Network className="size-4.5" />
            </div>
            <div className="min-w-0">
              <h3 id="edge-candidates-title" className="text-sm font-extrabold text-foreground leading-tight">
                Edge Candidate Decisions
              </h3>
              <p className="text-[10px] text-muted-foreground/85 font-medium mt-0.5 leading-none">
                {hasActionableCandidates
                  ? `${actionableCandidates.length} pending connections staged for approval.`
                  : `${selectedCandidates.length} finished candidate decisions.`}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2">
            <Badge
              variant="outline"
              className="rounded-full border-primary/10 bg-background px-2.5 py-1 text-[9px] font-black uppercase tracking-widest text-primary"
            >
              {reviewCommitStatus}
            </Badge>
            {hasActionableCandidates ? (
              <>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleToggleSelectAll}
                  className="h-8 px-3 rounded-lg border-primary/20 hover:border-primary/40 bg-card/65 font-bold transition-all text-xs flex items-center gap-1"
                >
                  {isAllSelected ? 'Deselect All' : 'Select All'}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => requestExitReview('abort')}
                  disabled={isCommitting || commitSubmitted}
                  className="h-8 rounded-lg border-destructive/20 bg-destructive/5 px-3 text-xs font-extrabold text-destructive hover:border-destructive/50 hover:bg-destructive/10"
                >
                  <XIcon className="size-3.5" />
                  Abort
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => void handleCommitReviewTask()}
                  disabled={!allCandidatesDecided || isCommitting || commitSubmitted}
                  className="h-8 rounded-lg bg-primary px-3.5 text-xs font-extrabold text-primary-foreground hover:bg-primary/95 disabled:opacity-45"
                >
                  <CheckIcon className="size-3.5" />
                  {isCommitting
                    ? 'Committing'
                    : commitSubmitted
                      ? 'Committed'
                      : 'Commit'}
                </Button>
              </>
            ) : (
              <Badge
                variant="secondary"
                className="rounded-full bg-muted px-2.5 py-1 text-[10px] font-black text-muted-foreground"
              >
                Finished archive
              </Badge>
            )}
          </div>
        </div>

        <div className="review-candidate-workspace-grid grid min-h-0 flex-1 items-stretch gap-3.5 2xl:grid-cols-[minmax(22rem,30rem)_minmax(0,1fr)]">
          <aside className="review-candidate-queue-shell flex h-full min-h-[18rem] min-w-0 flex-col overflow-hidden rounded-2xl border border-primary/10 bg-card/60 shadow-sm 2xl:min-h-0">
            <div className="shrink-0 border-b border-border/45 bg-muted/10 p-3.5">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                    Candidate Queue
                  </p>
                  <p className="mt-1 text-xs font-extrabold text-foreground">
                    {selectedCandidates.length} edge candidates
                  </p>
                </div>
                <div className="flex items-center gap-1.5">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => setIsFilterExpanded(!isFilterExpanded)}
                    className={cn(
                      "size-7 rounded-lg border-border/45 bg-background/50 hover:bg-muted/30 transition-all cursor-pointer",
                      isFilterExpanded && "border-primary/30 bg-primary/5 text-primary"
                    )}
                    title="Filter / Sort Options"
                  >
                    <SlidersHorizontal className="size-3.5" />
                  </Button>
                  <Badge
                    variant="outline"
                    className="rounded-full border-primary/15 bg-background px-2 py-0.5 text-[9px] font-black text-primary"
                  >
                    {hasActionableCandidates
                      ? `${draftDecisionCount}/${actionableCandidates.length}`
                      : `${selectedCandidates.length} done`}
                  </Badge>
                </div>
              </div>

              {isFilterExpanded && (
                <div className="mt-3 flex flex-col gap-2 rounded-xl bg-muted/15 border border-border/35 p-2.5 animate-in fade-in slide-in-from-top-1 duration-200">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 text-[9px] font-black uppercase tracking-widest text-muted-foreground">
                      <Layers className="size-3 text-primary" />
                      <span>Page Size</span>
                    </div>
                    <div className="flex items-center gap-0.5 rounded-lg bg-muted/50 p-0.5 border border-border/20 w-24">
                      <button
                        type="button"
                        disabled={reviewControlsDisabled}
                        onClick={() => handleCandidatePageSizeChange(5)}
                        className={cn(
                          "flex-1 rounded-md py-0.5 text-[9px] font-black transition-all cursor-pointer disabled:opacity-40 select-none",
                          candidatePageSize === 5
                            ? "bg-card text-foreground shadow-xs border border-border/35"
                            : "text-muted-foreground/80 hover:text-foreground"
                        )}
                      >
                        5
                      </button>
                      <button
                        type="button"
                        disabled={reviewControlsDisabled}
                        onClick={() => handleCandidatePageSizeChange(10)}
                        className={cn(
                          "flex-1 rounded-md py-0.5 text-[9px] font-black transition-all cursor-pointer disabled:opacity-40 select-none",
                          candidatePageSize === 10
                            ? "bg-card text-foreground shadow-xs border border-border/35"
                            : "text-muted-foreground/80 hover:text-foreground"
                        )}
                      >
                        10
                      </button>
                    </div>
                  </div>

                  <div className="h-px bg-border/20" />

                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 text-[9px] font-black uppercase tracking-widest text-muted-foreground">
                      <ArrowUpDown className="size-3 text-primary" />
                      <span>Sort By</span>
                    </div>
                    <div className="flex items-center gap-0.5 rounded-lg bg-muted/50 p-0.5 border border-border/20 w-44">
                      <button
                        type="button"
                        disabled={reviewControlsDisabled}
                        onClick={() => handleCandidateSortModeChange('default')}
                        className={cn(
                          "flex-1 rounded-md py-0.5 text-[9px] font-black transition-all cursor-pointer disabled:opacity-40 truncate px-1 select-none",
                          candidateSortMode === 'default'
                            ? "bg-card text-foreground shadow-xs border border-border/35"
                            : "text-muted-foreground/80 hover:text-foreground"
                        )}
                      >
                        기본
                      </button>
                      <button
                        type="button"
                        disabled={reviewControlsDisabled}
                        onClick={() => handleCandidateSortModeChange('confidence_desc')}
                        className={cn(
                          "flex-1 rounded-md py-0.5 text-[9px] font-black transition-all cursor-pointer disabled:opacity-40 truncate px-1 select-none",
                          candidateSortMode === 'confidence_desc'
                            ? "bg-card text-foreground shadow-xs border border-border/35"
                            : "text-muted-foreground/80 hover:text-foreground"
                        )}
                        title="Accuracy 높은 순"
                      >
                        Acc. ↑
                      </button>
                      <button
                        type="button"
                        disabled={reviewControlsDisabled}
                        onClick={() => handleCandidateSortModeChange('confidence_asc')}
                        className={cn(
                          "flex-1 rounded-md py-0.5 text-[9px] font-black transition-all cursor-pointer disabled:opacity-40 truncate px-1 select-none",
                          candidateSortMode === 'confidence_asc'
                            ? "bg-card text-foreground shadow-xs border border-border/35"
                            : "text-muted-foreground/80 hover:text-foreground"
                        )}
                        title="Accuracy 낮은 순"
                      >
                        Acc. ↓
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto p-2.5 pr-2 overscroll-contain [scrollbar-gutter:stable]
              [&::-webkit-scrollbar]:w-1.5
              [&::-webkit-scrollbar-track]:rounded-full
              [&::-webkit-scrollbar-track]:bg-muted/10
              [&::-webkit-scrollbar-thumb]:rounded-full
              [&::-webkit-scrollbar-thumb]:bg-primary/20
              hover:[&::-webkit-scrollbar-thumb]:bg-primary/40"
            >
              <div className="grid gap-2">
                {paginatedCandidates.map((candidate, index) => (
                  <ReviewCandidateListItem
                    key={candidate.id}
                    candidate={candidate}
                    index={candidatePageStart + index}
                    selected={candidate.id === activeCandidate?.id}
                    disabled={reviewControlsDisabled || !isPendingReviewCandidate(candidate)}
                    checked={Boolean(scopedCheckedIds[candidate.id])}
                    draftAction={scopedDraftDecisions[candidate.id]?.action ?? null}
                    confidenceScore={getReviewCandidateConfidenceScore(candidate)}
                    onSelect={() => setActiveCandidateId(
                      candidate.id === activeCandidate?.id ? null : candidate.id,
                    )}
                    onCheckedChange={(checked) => handleCheckedChange(candidate.id, checked)}
                  />
                ))}
              </div>
            </div>

            <div className="flex shrink-0 items-center justify-between gap-2 border-t border-border/45 bg-muted/10 p-3">
              <p className="text-[10px] font-bold text-muted-foreground">
                {selectedCandidates.length === 0
                  ? '0 candidates'
                  : `${candidatePageStart + 1}-${candidatePageEnd} / ${selectedCandidates.length}`}
              </p>
              <div className="flex items-center gap-1.5">
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => handleCandidatePageChange(effectiveCandidatePage - 1)}
                  disabled={effectiveCandidatePage <= 1}
                  className="size-7 rounded-lg border-primary/15 bg-background"
                  aria-label="Previous candidate page"
                >
                  <ChevronLeft className="size-3.5" aria-hidden="true" />
                </Button>
                <span className="min-w-12 text-center text-[10px] font-black text-foreground">
                  {effectiveCandidatePage}/{candidatePageCount}
                </span>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => handleCandidatePageChange(effectiveCandidatePage + 1)}
                  disabled={effectiveCandidatePage >= candidatePageCount}
                  className="size-7 rounded-lg border-primary/15 bg-background"
                  aria-label="Next candidate page"
                >
                  <ChevronRight className="size-3.5" aria-hidden="true" />
                </Button>
              </div>
            </div>
          </aside>

          <div className="review-candidate-detail-shell flex h-full min-h-[28rem] flex-col self-stretch 2xl:min-h-0">
            <ReviewCandidateDetailPanel
              candidate={activeCandidate}
              disabled={reviewControlsDisabled || activeCandidateReadOnly}
              readOnly={activeCandidateReadOnly}
              checked={activeCandidate ? Boolean(scopedCheckedIds[activeCandidate.id]) : false}
              draftAction={activeCandidate ? scopedDraftDecisions[activeCandidate.id]?.action ?? null : null}
              note={activeCandidateNote}
              editedRationale={activeCandidateEditedRationale}
              onNoteChange={(note) => activeCandidate && updateCandidateAnnotation(activeCandidate.id, { note })}
              onCheckedChange={(checked) => activeCandidate && handleCheckedChange(activeCandidate.id, checked)}
              onDecision={handleSingleDecision}
              sourceDocument={activeDocumentRefs.sourceDoc}
              targetDocument={activeDocumentRefs.targetDoc}
              reviewDocumentTitle={selectedDocumentName}
              confidenceScore={activeCandidate ? getReviewCandidateConfidenceScore(activeCandidate) : undefined}
            />
          </div>
        </div>

      </section>

      <ReviewExitDialog
        open={exitDialogOpen}
        intent={exitDialogIntent}
        draftedCount={draftDecisionCount}
        remainingCount={remainingDecisionCount}
        onOpenChange={setExitDialogOpen}
        onConfirm={confirmExitReview}
      />
    </div>
  )
}


function BackToQueueButton({ onBack }: { onBack: () => void }) {
  return (
    <Button
      type="button"
      variant="outline"
      onClick={onBack}
      className="border-primary/20 hover:border-primary/50 rounded-xl transition-all h-9 px-3 text-xs"
    >
      <ArrowLeft data-icon="inline-start" className="size-3.5 text-primary" aria-hidden="true" />
      Back To Queue
    </Button>
  )
}

function ReviewExitDialog({
  open,
  intent,
  draftedCount,
  remainingCount,
  onOpenChange,
  onConfirm,
}: {
  open: boolean
  intent: 'back' | 'abort'
  draftedCount: number
  remainingCount: number
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md rounded-2xl border border-destructive/20 bg-card p-0 shadow-2xl">
        <DialogHeader className="border-b border-border/45 bg-muted/15 p-5">
          <div className="flex items-center gap-3">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-xl border border-destructive/20 bg-destructive/10 text-destructive">
              <AlertTriangle className="size-4.5" />
            </div>
            <div>
              <DialogTitle className="text-sm font-extrabold text-foreground">
                {intent === 'abort' ? 'Abort review task?' : 'Leave review task?'}
              </DialogTitle>
              <DialogDescription className="mt-1 text-xs leading-relaxed">
                Commit하지 않은 review draft는 backend에 저장되지 않습니다.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="grid gap-2 px-5 py-4 text-xs font-semibold text-muted-foreground">
          <p>
            Drafted decisions: <span className="font-black text-foreground">{draftedCount}</span>
          </p>
          <p>
            Remaining decisions: <span className="font-black text-foreground">{remainingCount}</span>
          </p>
          <p className="rounded-xl border border-destructive/15 bg-destructive/5 p-3 text-[11px] leading-relaxed text-destructive">
            지금까지 선택한 approve/deny draft는 전부 버려집니다. 계속하시겠습니까?
          </p>
        </div>

        <DialogFooter className="m-0 rounded-b-2xl border-t border-border/45 bg-muted/15 p-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="h-9 rounded-xl px-4 text-xs font-bold"
          >
            Continue Review
          </Button>
          <Button
            type="button"
            onClick={onConfirm}
            className="h-9 rounded-xl bg-destructive px-4 text-xs font-extrabold text-destructive-foreground hover:bg-destructive/90"
          >
            Discard Draft
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function buildDecisionNote(
  candidate: RelationshipCandidate | undefined,
  note: string,
  editedRationale?: string,
) {
  const trimmedNote = note.trim()
  const trimmedRationale = editedRationale?.trim() ?? ''
  const isRationaleEdited =
    Boolean(trimmedRationale) &&
    candidate !== undefined &&
    trimmedRationale !== (candidate.rationale || '').trim()

  if (!isRationaleEdited) {
    return trimmedNote || null
  }

  return `[AI Rationale Annotated]: ${trimmedRationale}\n\n[Reviewer Decision Note]: ${trimmedNote}`
}

function findNextUndecidedCandidateId(
  candidates: RelationshipCandidate[],
  currentCandidateId: string,
  draftDecisions: Record<string, DraftReviewDecision>,
) {
  const currentIndex = candidates.findIndex((candidate) => candidate.id === currentCandidateId)
  const orderedCandidates = currentIndex === -1
    ? candidates
    : [
      ...candidates.slice(currentIndex + 1),
      ...candidates.slice(0, currentIndex),
    ]

  return orderedCandidates.find((candidate) => (
    isPendingReviewCandidate(candidate) && !draftDecisions[candidate.id]
  ))?.id ?? null
}

function getCandidatePageForId(
  candidates: RelationshipCandidate[],
  candidateId: string | null,
  pageSize: number,
) {
  if (!candidateId) {
    return null
  }

  const candidateIndex = candidates.findIndex((candidate) => candidate.id === candidateId)
  if (candidateIndex === -1) {
    return null
  }

  return Math.floor(candidateIndex / pageSize) + 1
}

function filterByCandidateIds<T>(
  record: Record<string, T>,
  candidateIds: Set<string>,
) {
  const next: Record<string, T> = {}
  Object.entries(record).forEach(([candidateId, value]) => {
    if (candidateIds.has(candidateId)) {
      next[candidateId] = value
    }
  })
  return next
}

function readReviewStatusFilter(value: string | null): ReviewCandidateStatusFilter {
  if (value === 'finished' || value === 'all') {
    return value
  }
  return 'pending'
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

function isPendingReviewCandidate(candidate: RelationshipCandidate) {
  return candidate.status.toLowerCase() === 'pending_review'
}

function getCandidateReviewNote(candidate: RelationshipCandidate) {
  return (
    candidate.review_note ??
    getMetadataString(candidate, ['review_note', 'reviewer_note']) ??
    ''
  )
}

function sortReviewCandidates(
  candidates: RelationshipCandidate[],
  sortMode: CandidateSortMode,
) {
  if (sortMode === 'default') {
    return candidates
  }

  const direction = sortMode === 'confidence_desc' ? -1 : 1
  return [...candidates].sort((left, right) => {
    const leftScore = getReviewCandidateConfidenceScore(left)
    const rightScore = getReviewCandidateConfidenceScore(right)
    const scoreDiff = (leftScore - rightScore) * direction
    if (scoreDiff !== 0) {
      return scoreDiff
    }
    return left.id.localeCompare(right.id)
  })
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

function getCandidateDocumentRefs(
  candidate: RelationshipCandidate,
  documents: RagDocument[],
) {
  const sourceLabel =
    getMetadataString(candidate, ['document_title', 'source_document_title', 'file_name']) ??
    candidate.job_id
  const targetLabel =
    getMetadataString(candidate, ['target_document_title', 'document_title', 'file_name']) ??
    candidate.job_id

  const sourceDoc =
    documents.find(
      (document) =>
        document.file_name === sourceLabel ||
        document.source_title === sourceLabel ||
        document.job_id === candidate.job_id,
    ) || null
  const targetDoc =
    documents.find(
      (document) =>
        document.file_name === targetLabel ||
        document.source_title === targetLabel ||
        document.job_id === candidate.job_id,
    ) || null

  return { sourceDoc, targetDoc }
}

function sameDisplayText(left: string | null | undefined, right: string | null | undefined) {
  const normalizedLeft = normalizeDisplayText(left)
  const normalizedRight = normalizeDisplayText(right)

  return Boolean(normalizedLeft && normalizedRight && normalizedLeft === normalizedRight)
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
    const normalized = normalizeDisplayText(value)
    if (!normalized) {
      continue
    }
    if (options.skipUuid && isUuidLike(normalized)) {
      continue
    }
    return normalized
  }

  return null
}

function normalizeDisplayText(value: string | null | undefined) {
  const trimmed = value?.trim()
  if (!trimmed || trimmed.toLowerCase() === 'unknown') {
    return null
  }

  return trimmed.split('/').pop()?.normalize('NFC') || trimmed.normalize('NFC')
}

function stripKnownExtension(value: string) {
  return value.replace(/\.(toon|md|markdown|txt|json|pdf|docx?)$/i, '')
}

function isUuidLike(value: string) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
}
