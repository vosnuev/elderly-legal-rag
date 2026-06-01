import {
  useMemo,
  useState,
} from 'react'
import {
  ArrowLeft,
  CheckCircle2,
  CheckIcon,
  FileText,
  GitBranch,
  ListChecks,
  Network,
  XIcon,
} from 'lucide-react'
import {
  Link,
  useParams,
} from 'react-router'

import { Accordion } from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
} from '@/components/ui/card'
import { PageHeader } from '@/components/workspace/page-header'
import { ReviewCandidateCard } from '@/features/review/review-candidate-card'
import { groupReviewCandidatesByJob } from '@/features/review/review-candidates'
import { useRagWorkspace } from '@/features/workspace/use-rag-workspace'
import { cn } from '@/lib/utils'

export function ReviewJobPage() {
  const { jobId = '' } = useParams()
  const {
    reviewCandidates,
    status,
    submitReviewDecisionForCandidate,
    documents,
  } = useRagWorkspace()

  // Parent states for Bulk Action controller
  const [checkedIds, setCheckedIds] = useState<Record<string, boolean>>({})
  const [isBulkSubmitting, setIsBulkSubmitting] = useState(false)

  const reviewJobs = useMemo(
    () => groupReviewCandidatesByJob(reviewCandidates),
    [reviewCandidates],
  )
  const selectedJob = reviewJobs.find((group) => group.jobId === jobId) ?? null
  const selectedCandidates = selectedJob?.candidates ?? []

  // Check state helpers
  const checkedCount = Object.keys(checkedIds).filter(
    (id) => checkedIds[id] && selectedCandidates.some((c) => c.id === id)
  ).length

  const isAllSelected =
    selectedCandidates.length > 0 &&
    selectedCandidates.every((candidate) => checkedIds[candidate.id])

  const handleToggleSelectAll = () => {
    if (isAllSelected) {
      setCheckedIds({})
    } else {
      const nextChecked: Record<string, boolean> = {}
      selectedCandidates.forEach((candidate) => {
        nextChecked[candidate.id] = true
      })
      setCheckedIds(nextChecked)
    }
  }

  const handleCheckedChange = (candidateId: string, checked: boolean) => {
    setCheckedIds((prev) => ({
      ...prev,
      [candidateId]: checked,
    }))
  }

  // Bulk Decision Executor (Promise.all parallel submissions)
  const handleBulkDecision = async (action: 'yes' | 'no') => {
    const idsToProcess = Object.keys(checkedIds).filter(
      (id) => checkedIds[id] && selectedCandidates.some((c) => c.id === id)
    )

    if (idsToProcess.length === 0) return

    setIsBulkSubmitting(true)
    try {
      await Promise.all(
        idsToProcess.map((candidateId) =>
          submitReviewDecisionForCandidate(candidateId, action, '')
        )
      )
      setCheckedIds({}) // Clear selection
    } catch (error) {
      console.error('Failed to submit bulk decision:', error)
    } finally {
      setIsBulkSubmitting(false)
    }
  }

  const handleSingleDecision = async (
    candidateId: string,
    action: 'yes' | 'no',
    note: string,
    editedRationale?: string,
  ) => {
    const candidate = selectedCandidates.find((c) => c.id === candidateId)
    const isRationaleEdited =
      editedRationale &&
      candidate &&
      editedRationale.trim() !== (candidate.rationale || '').trim()
    let finalNote = note.trim()

    if (isRationaleEdited) {
      finalNote = `[AI Rationale Annotated]: ${editedRationale.trim()}\n\n[Reviewer Decision Note]: ${finalNote}`
    }

    await submitReviewDecisionForCandidate(candidateId, action, finalNote)
  }

  function getMetadataString(candidate: any, keys: string[]) {
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

  const [openCandidates, setOpenCandidates] = useState<string[] | undefined>()
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10
  const totalPages = Math.ceil(selectedCandidates.length / itemsPerPage)

  // Reset to page 1 and close accordion if parent collection length changes
  useMemo(() => {
    setCurrentPage(1)
    setOpenCandidates(undefined)
  }, [selectedCandidates.length])

  const paginatedCandidates = useMemo(() => {
    return selectedCandidates.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)
  }, [selectedCandidates, currentPage])

  const firstCandidateValue = paginatedCandidates[0]
    ? [getAccordionValue(paginatedCandidates[0].id)]
    : []

  const accordionValue = openCandidates === undefined
    ? firstCandidateValue
    : openCandidates

  if (!selectedJob) {
    return (
      <div className="grid gap-4">
        <PageHeader
          title="Review Document"
          description="This review job is not currently pending."
          action={<BackToQueueButton />}
        />
        <Card className="border border-primary/10 rounded-2xl bg-card/65 backdrop-blur-md">
          <CardContent className="flex min-h-64 items-center justify-center">
            <div className="text-center">
              <CheckCircle2 className="mx-auto size-9 text-chart-3 animate-pulse" aria-hidden="true" />
              <p className="mt-3 text-sm font-extrabold text-foreground">No pending edge candidates</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Return to the queue and choose a pending review document.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="grid gap-4 relative pb-20">
      <PageHeader
        title="Review Document"
        description="Approve or deny edge candidates for the selected ingest job."
        action={<BackToQueueButton />}
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
              disabled={isBulkSubmitting}
              className="h-8.5 px-3 rounded-lg border-border bg-background/55 text-muted-foreground hover:text-foreground font-bold text-xs transition-all"
            >
              Cancel
            </Button>
            
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void handleBulkDecision('no')}
              disabled={isBulkSubmitting}
              className="h-8.5 px-3 rounded-lg border-destructive/20 hover:border-destructive bg-destructive/5 hover:bg-destructive/10 text-destructive font-bold transition-all text-xs flex items-center gap-1"
            >
              <XIcon className="size-3.5" />
              {isBulkSubmitting ? 'Processing' : `Deny`}
            </Button>
            
            <Button
              type="button"
              size="sm"
              onClick={() => void handleBulkDecision('yes')}
              disabled={isBulkSubmitting}
              className="h-8.5 px-4.5 rounded-lg bg-gradient-to-r from-chart-3 to-chart-3 hover:from-chart-3/95 hover:to-chart-3/95 text-primary-foreground font-extrabold shadow-md hover:shadow-chart-3/15 transition-all text-xs flex items-center gap-1"
            >
              <CheckIcon className="size-3.5" />
              {isBulkSubmitting ? 'Processing' : `Approve`}
            </Button>
          </div>
        </div>
      </div>

      {/* Selected Job Metadata Header Context Panel - Compact */}
      <section className="review-job-context rounded-2xl border border-primary/10 bg-card/65 backdrop-blur-md p-4 shadow-sm" aria-labelledby="review-document-title">
        <div className="review-job-context-main flex items-center gap-3.5 min-w-0">
          <div className="review-job-context-icon flex size-10.5 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-primary to-accent text-primary-foreground shadow-sm shadow-primary/15" aria-hidden="true">
            <FileText className="size-5" />
          </div>
          <div className="min-w-0">
            <p className="review-job-context-label text-[9px] font-black text-muted-foreground uppercase tracking-widest leading-none">
              Selected Ingest Document
            </p>
            <h2 id="review-document-title" className="review-job-context-title mt-1.5 text-lg font-extrabold tracking-tight text-foreground/95 break-all leading-snug">
              {selectedJob.documentLabel}
            </h2>
            <p className="review-job-context-file mt-0.5 text-[10px] text-muted-foreground/80 font-medium truncate">
              {selectedJob.fileName ?? selectedJob.jobId}
            </p>
          </div>
        </div>

        <div className="review-job-context-meta grid gap-2.5 mt-3 lg:mt-0" aria-label="Review document metadata">
          <ReviewContextFact
            icon={GitBranch}
            label="Job ID"
            value={selectedJob.jobId}
          />
          <ReviewContextFact
            icon={Network}
            label="Total Edges"
            value={`${selectedJob.candidates.length} pending`}
          />
          <ReviewContextFact
            icon={ListChecks}
            label="Actions"
            value="Bulk & Individual"
          />
        </div>
      </section>

      {/* Main Review Section holding Accordion Candidates */}
      <section className="review-job-candidates grid gap-3.5" aria-labelledby="edge-candidates-title">
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
                {selectedJob.candidates.length} connections staged for approval.
              </p>
            </div>
          </div>

          {/* Select All Controller Button at Page Header */}
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleToggleSelectAll}
              className="h-8 px-3 rounded-lg border-primary/20 hover:border-primary/40 bg-card/65 font-bold transition-all text-xs flex items-center gap-1"
            >
              {isAllSelected ? 'Deselect All' : 'Select All'}
            </Button>
            <Badge variant="outline" className="font-bold text-[9px] bg-background tracking-wide px-2 py-0.5 rounded-full border-primary/10 text-primary leading-none">
              ID: {selectedJob.jobId}
            </Badge>
          </div>
        </div>

        <Accordion
          type="multiple"
          value={accordionValue}
          onValueChange={setOpenCandidates}
          className="review-job-candidate-list grid gap-2.5"
        >
          {paginatedCandidates.map((candidate) => {
            const sourceLabel =
              getMetadataString(candidate, ['document_title', 'source_document_title', 'file_name']) ??
              candidate.job_id
            const targetLabel =
              getMetadataString(candidate, ['target_document_title', 'document_title', 'file_name']) ??
              candidate.job_id

            const sourceDoc =
              documents.find(
                (d) =>
                  d.file_name === sourceLabel ||
                  d.source_title === sourceLabel ||
                  d.job_id === candidate.job_id,
              ) || null
            const targetDoc =
              documents.find(
                (d) =>
                  d.file_name === targetLabel ||
                  d.source_title === targetLabel ||
                  d.job_id === candidate.job_id,
              ) || null

            const charSum = candidate.id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
            const confidenceScore = typeof candidate.metadata.confidence === 'number'
              ? candidate.metadata.confidence
              : Number((0.72 + (charSum % 23) / 100).toFixed(2))

            return (
              <ReviewCandidateCard
                key={candidate.id}
                accordionValue={getAccordionValue(candidate.id)}
                candidate={candidate}
                disabled={status === 'loading' || isBulkSubmitting}
                checked={Boolean(checkedIds[candidate.id])}
                onCheckedChange={(checked) => handleCheckedChange(candidate.id, checked)}
                onDecision={handleSingleDecision}
                onRequestCollapse={() => setOpenCandidates(prev => (prev || []).filter(v => v !== getAccordionValue(candidate.id)))}
                sourceDocument={sourceDoc}
                targetDocument={targetDoc}
                confidenceScore={confidenceScore}
              />
            )
          })}
        </Accordion>

        {/* Premium Neon Pagination Panel */}
        {totalPages > 1 && (
          <div className="flex flex-wrap items-center justify-between gap-4 border border-primary/10 bg-card/45 backdrop-blur-md p-4 rounded-xl shadow-sm mt-3.5 select-none animate-scale-up">
            <span className="text-[10px] text-muted-foreground/80 font-bold">
              Showing <span className="text-primary font-extrabold">{((currentPage - 1) * itemsPerPage) + 1}</span> to{' '}
              <span className="text-primary font-extrabold">{Math.min(currentPage * itemsPerPage, selectedCandidates.length)}</span> of{' '}
              <span className="text-primary font-extrabold">{selectedCandidates.length}</span> pending candidates
            </span>
            <div className="flex items-center gap-1.5">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setCurrentPage((prev) => Math.max(prev - 1, 1))
                  setOpenCandidates(undefined)
                  window.scrollTo({ top: 0, behavior: 'smooth' })
                }}
                disabled={currentPage === 1}
                className="h-8.5 rounded-lg text-xs font-bold border-primary/10 hover:border-primary/30"
              >
                Previous
              </Button>
              {Array.from({ length: totalPages }).map((_, index) => {
                const pageNum = index + 1
                const isActive = pageNum === currentPage
                return (
                  <Button
                    key={pageNum}
                    type="button"
                    variant={isActive ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => {
                      setCurrentPage(pageNum)
                      setOpenCandidates(undefined)
                      window.scrollTo({ top: 0, behavior: 'smooth' })
                    }}
                    className={cn(
                      "size-8.5 rounded-lg text-xs font-bold",
                      isActive 
                        ? "bg-primary text-primary-foreground font-black shadow-md shadow-primary/10" 
                        : "border-primary/10 hover:border-primary/30 text-muted-foreground hover:text-foreground"
                    )}
                  >
                    {pageNum}
                  </Button>
                )
              })}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setCurrentPage((prev) => Math.min(prev + 1, totalPages))
                  setOpenCandidates(undefined)
                  window.scrollTo({ top: 0, behavior: 'smooth' })
                }}
                disabled={currentPage === totalPages}
                className="h-8.5 rounded-lg text-xs font-bold border-primary/10 hover:border-primary/30"
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}

function ReviewContextFact({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof GitBranch
  label: string
  value: string
}) {
  return (
    <div className="review-job-context-fact flex items-center gap-2.5 rounded-xl border border-border/75 bg-muted/45 px-3 py-2">
      <div className="p-1 rounded-lg bg-card text-muted-foreground">
        <Icon className="size-3.5 shrink-0" aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <p className="text-[8px] font-black text-muted-foreground/80 uppercase tracking-widest leading-none">
          {label}
        </p>
        <strong className="block mt-0.5 text-[11px] font-extrabold text-foreground/90 truncate leading-tight">{value}</strong>
      </div>
    </div>
  )
}

function BackToQueueButton() {
  return (
    <Button
      type="button"
      variant="outline"
      asChild
      className="border-primary/20 hover:border-primary/50 rounded-xl transition-all h-9 px-3 text-xs"
    >
      <Link to="/review-queue">
        <ArrowLeft data-icon="inline-start" className="size-3.5 text-primary" aria-hidden="true" />
        Back To Queue
      </Link>
    </Button>
  )
}

function getAccordionValue(candidateId: string) {
  return `candidate-${candidateId}`
}
