import {
  CheckIcon,
  ChevronDown,
  FileText,
  GitBranch,
  XIcon,
  Sparkles,
  BookOpen,
  TrendingUp,
  Network,
} from 'lucide-react'
import {
  useId,
  useState,
} from 'react'
import { cn } from '@/lib/utils'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
} from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  formatReviewCandidateConfidence,
  getReviewCandidateConfidenceBadgeClass,
  getReviewCandidateConfidenceScore,
} from '@/features/review/review-candidate-utils'
import type {
  RelationshipCandidate,
  ReviewAction,
  RagDocument,
} from '@/types'

type ReviewDecisionAction = Extract<ReviewAction, 'yes' | 'no'>

type ReviewCandidateListItemProps = {
  candidate: RelationshipCandidate
  index: number
  selected: boolean
  disabled?: boolean
  checked?: boolean
  draftAction?: ReviewDecisionAction | null
  confidenceScore?: number
  onSelect: () => void
  onCheckedChange?: (checked: boolean) => void
}

type ReviewCandidateDetailPanelProps = {
  candidate: RelationshipCandidate | null
  disabled?: boolean
  readOnly?: boolean
  checked?: boolean
  draftAction?: ReviewDecisionAction | null
  note: string
  editedRationale: string
  onNoteChange: (note: string) => void
  onCheckedChange?: (checked: boolean) => void
  onDecision: (
    candidateId: string,
    action: ReviewDecisionAction,
    note: string,
    editedRationale?: string,
  ) => Promise<void> | void
  sourceDocument?: RagDocument | null
  targetDocument?: RagDocument | null
  reviewDocumentTitle?: string | null
  confidenceScore?: number
}

type ChunkNodePanelProps = {
  kind: 'source' | 'target'
  nodeId: string
  displayLabel: string
  description: string | null
  text: string
  documentTitle: string
  hasFullDoc: boolean
  onOpenDoc: () => void
}

// Clean and Transparent Raw Text Viewer preserving document layouts
function RawTextViewer({ text }: { text: string }) {
  if (!text) {
    return <p className="text-muted-foreground italic text-[10px]">Context chunk data is empty.</p>
  }

  return (
    <div className="whitespace-pre-wrap break-all text-[11px] font-mono leading-relaxed text-foreground/90 tracking-tight select-text">
      {text}
    </div>
  )
}

export function ReviewCandidateListItem({
  candidate,
  index,
  selected,
  disabled = false,
  checked = false,
  draftAction = null,
  confidenceScore,
  onSelect,
  onCheckedChange,
}: ReviewCandidateListItemProps) {
  const sourceChunk = getSourceChunk(candidate)
  const targetChunk = getTargetChunk(candidate)
  const confidence = getReviewCandidateConfidenceScore(candidate, confidenceScore)
  const relationshipLabel = formatMachineLabel(candidate.relationship_type)
  const statusLabel = formatCandidateStatus(candidate.status)

  const handleCheckedChange = (value: boolean | 'indeterminate') => {
    onCheckedChange?.(value === true)
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onSelect()
        }
      }}
      className={cn(
        'group relative min-w-0 w-full cursor-pointer overflow-hidden rounded-xl border bg-card/80 p-3 pl-4 text-left shadow-sm outline-none transition-all hover:border-primary/45 hover:bg-muted/35 hover:shadow-md focus-visible:ring-2 focus-visible:ring-primary/35',
        selected
          ? 'border-primary bg-primary/10 shadow-lg shadow-primary/10 ring-2 ring-primary/20'
          : 'border-border/65',
      )}
    >
      <span
        className={cn(
          'absolute inset-y-2 left-0 w-1 rounded-r-full transition-colors',
          selected ? 'bg-primary' : 'bg-transparent group-hover:bg-primary/30',
        )}
        aria-hidden="true"
      />
      <div className="flex items-start gap-2.5">
        <div
          className={cn(
            'mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg border text-[10px] font-black',
            selected
              ? 'border-primary/30 bg-primary/15 text-primary'
              : 'border-border bg-background text-muted-foreground',
          )}
          aria-hidden="true"
        >
          {index + 1}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-start justify-between gap-2">
            <p className="line-clamp-2 text-[12px] font-extrabold leading-snug text-foreground">
              {sourceChunk.displayLabel}
            </p>
            <Checkbox
              checked={checked}
              onClick={(event) => event.stopPropagation()}
              onCheckedChange={handleCheckedChange}
              disabled={disabled}
              aria-label="Select candidate for bulk staging"
              className="mt-0.5 size-3.5 shrink-0 rounded border-primary/35"
            />
          </div>
          <div className="mt-1 flex items-center gap-1.5 text-[9px] font-black uppercase tracking-wider text-muted-foreground">
            <span className="max-w-[8rem] truncate">{relationshipLabel}</span>
            <span aria-hidden="true">→</span>
            <span className="min-w-0 flex-1 truncate text-chart-2">{targetChunk.displayLabel}</span>
          </div>
          <p className="mt-2 line-clamp-2 text-[10px] font-medium leading-relaxed text-muted-foreground">
            {candidate.rationale || candidate.evidence_text || targetChunk.description || sourceChunk.description}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <Badge
              variant="outline"
              className={cn(
                'rounded-full px-1.5 py-0 text-[8px] font-black',
                getReviewCandidateConfidenceBadgeClass(confidence),
              )}
            >
              {formatReviewCandidateConfidence(confidence)}
            </Badge>
            <Badge
              variant="outline"
              className="rounded-full border-primary/15 bg-primary/5 px-1.5 py-0 text-[8px] font-black text-primary"
            >
              {statusLabel}
            </Badge>
            {draftAction && (
              <Badge
                variant="outline"
                className={cn(
                  'rounded-full px-1.5 py-0 text-[8px] font-black',
                  draftAction === 'yes'
                    ? 'border-chart-3/30 bg-chart-3/10 text-chart-3'
                    : 'border-destructive/30 bg-destructive/10 text-destructive',
                )}
              >
                {draftAction === 'yes' ? 'Approve draft' : 'Deny draft'}
              </Badge>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export function ReviewCandidateDetailPanel({
  candidate,
  disabled = false,
  readOnly = false,
  checked = false,
  draftAction = null,
  note,
  editedRationale,
  onNoteChange,
  onCheckedChange,
  onDecision,
  sourceDocument = null,
  targetDocument = null,
  reviewDocumentTitle = null,
  confidenceScore,
}: ReviewCandidateDetailPanelProps) {
  const noteId = useId()
  const [submittingAction, setSubmittingAction] = useState<ReviewDecisionAction | null>(null)
  const [docModalOpen, setDocModalOpen] = useState(false)
  const [activeDocTitle, setActiveDocTitle] = useState('')
  const [activeDocContent, setActiveDocContent] = useState('')

  const sourceChunk = candidate ? getSourceChunk(candidate) : null
  const targetChunk = candidate ? getTargetChunk(candidate) : null
  const isSubmitting = submittingAction !== null
  const finalConfidence = candidate
    ? getReviewCandidateConfidenceScore(candidate, confidenceScore)
    : 0

  if (!candidate || !sourceChunk || !targetChunk) {
    return (
      <Card className="review-candidate-empty-state relative flex h-full min-h-[28rem] flex-col items-center justify-center overflow-hidden rounded-2xl border border-primary/10 bg-card/60 p-6 text-center shadow-md backdrop-blur-sm">
        <div className="pointer-events-none absolute -top-36 -right-36 size-72 rounded-full bg-primary/4 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-36 -left-36 size-72 rounded-full bg-chart-2/4 blur-3xl" />

        <div className="relative z-10 mb-5 flex w-full max-w-[21rem] items-center justify-between gap-3 px-2">
          <div className="flex flex-col items-center gap-1">
            <div className="flex size-10 items-center justify-center rounded-xl border border-dashed border-primary/25 bg-primary/4 text-muted-foreground/55 shadow-inner">
              <FileText className="size-4.5" />
            </div>
            <span className="text-[8px] font-black uppercase tracking-wider text-muted-foreground/45">Source</span>
          </div>

          <div className="relative mt-[-0.65rem] flex flex-1 flex-col items-center gap-1.5">
            <div className="relative w-full border-t border-dashed border-border/65">
              <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-0.5 border-y-2.5 border-y-transparent border-l-[5px] border-l-border/65" />
            </div>
            <Badge variant="outline" className="flex shrink-0 items-center gap-1 rounded-full border-primary/15 bg-muted/45 px-1.5 py-0 text-[7.5px] font-black text-muted-foreground/70 shadow-xs">
              <Sparkles className="size-2 text-primary/80" />
              AI Extraction
            </Badge>
          </div>

          <div className="flex flex-col items-center gap-1">
            <div className="flex size-10 items-center justify-center rounded-xl border border-dashed border-primary/25 bg-primary/4 text-muted-foreground/55 shadow-inner">
              <GitBranch className="size-4.5" />
            </div>
            <span className="text-[8px] font-black uppercase tracking-wider text-muted-foreground/45">Target</span>
          </div>
        </div>

        <div className="relative z-10 max-w-[21rem]">
          <div className="mx-auto mb-2.5 flex size-9 items-center justify-center rounded-xl border border-primary/12 bg-primary/6 text-primary shadow-xs">
            <Network className="size-4.5" aria-hidden="true" />
          </div>
          <h3 className="text-[12px] font-black tracking-tight text-foreground">검토할 관계 후보를 선택하세요</h3>
          <p className="mt-1.5 text-[10px] font-semibold leading-relaxed text-muted-foreground">
            좌측 queue에서 후보를 선택하면 청크 원문, 추출 근거, review note가 열립니다.
          </p>

          <div className="mt-3 flex flex-wrap items-center justify-center gap-1.5 text-[8.5px] font-black text-muted-foreground/65">
            <span className="rounded-full border border-border/35 bg-muted/15 px-2 py-1">청크 비교</span>
            <span className="rounded-full border border-border/35 bg-muted/15 px-2 py-1">근거 확인</span>
            <span className="rounded-full border border-border/35 bg-muted/15 px-2 py-1">결정 기록</span>
          </div>
        </div>
      </Card>
    )
  }

  const sourceDocumentTitle = getChunkDocumentTitle({
    candidate,
    chunkDocumentLabel: sourceChunk.documentLabel,
    document: sourceDocument,
    fallbackTitle: reviewDocumentTitle,
    kind: 'source',
  })
  const relationshipLabel = formatMachineLabel(candidate.relationship_type)
  const statusLabel = formatCandidateStatus(candidate.status)
  const targetDocumentTitle = getChunkDocumentTitle({
    candidate,
    chunkDocumentLabel: targetChunk.documentLabel,
    document: targetDocument,
    fallbackTitle: reviewDocumentTitle,
    kind: 'target',
  })

  const handleCheckedChange = (value: boolean | 'indeterminate') => {
    onCheckedChange?.(value === true)
  }

  const handleDecision = async (action: ReviewDecisionAction) => {
    setSubmittingAction(action)
    try {
      await onDecision(candidate.id, action, note.trim(), editedRationale.trim())
    } finally {
      setSubmittingAction(null)
    }
  }

  const handleOpenDocument = (isSource: boolean) => {
    const doc = isSource ? sourceDocument : targetDocument
    const chunk = isSource ? sourceChunk : targetChunk
    const label = chunk.documentLabel

    if (doc) {
      setActiveDocTitle(doc.file_name || doc.source_title || label)
      setActiveDocContent(doc.content || 'Content not available.')
    } else {
      setActiveDocTitle(label)
      setActiveDocContent(
        isSource
          ? `--- VIRTUAL RUNTIME DATA REFERENCE ---\nDocument Label: ${label}\nChunk Node ID: ${candidate.source_chunk_id}\n\n[Raw Text Context Extract]:\n${sourceChunk.text}\n\n[System Info]: Fully ingested and stored in GraphRAG engine.`
          : `--- VIRTUAL RUNTIME DATA REFERENCE ---\nDocument Label: ${label}\nTarget Reference: ${candidate.target_node}\n\n[Raw Text Context Extract]:\n${targetChunk.text}\n\n[System Info]: Fully ingested and stored in GraphRAG engine.`
      )
    }
    setDocModalOpen(true)
  }

  return (
    <Card className="review-candidate-detail flex h-full min-h-[34rem] flex-col overflow-hidden rounded-2xl border border-primary/10 bg-card/70 shadow-md backdrop-blur-md">
      <CardHeader className="shrink-0 border-b border-border/45 bg-muted/10 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="max-w-[18rem] truncate rounded-lg border border-primary/15 bg-primary/8 px-2.5 py-1 font-extrabold text-primary">
                {sourceChunk.displayLabel}
              </span>
              <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                [{relationshipLabel}] →
              </span>
              <span className="max-w-[18rem] truncate rounded-lg border border-chart-2/15 bg-chart-2/8 px-2.5 py-1 font-extrabold text-chart-2">
                {targetChunk.displayLabel}
              </span>
            </div>
            <p className="mt-2 break-all text-[10px] font-semibold text-muted-foreground/80">
              Candidate ID: {candidate.id} · Version: {candidate.version} · Job: {candidate.job_id}
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Badge
              variant="outline"
              className={cn(
                'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-black',
                getReviewCandidateConfidenceBadgeClass(finalConfidence),
              )}
            >
              <TrendingUp className="mr-1 size-3" aria-hidden="true" />
              AI {formatReviewCandidateConfidence(finalConfidence)}
            </Badge>
            <Badge variant="secondary" className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary">
              {statusLabel}
            </Badge>
            {draftAction && (
              <Badge
                variant="outline"
                className={cn(
                  'rounded-full px-2 py-0.5 text-[10px] font-black',
                  draftAction === 'yes'
                    ? 'border-chart-3/30 bg-chart-3/10 text-chart-3'
                    : 'border-destructive/30 bg-destructive/10 text-destructive',
                )}
              >
                Draft: {draftAction === 'yes' ? 'Approve' : 'Deny'}
              </Badge>
            )}
            {!readOnly && (
              <label className="review-check-control cursor-pointer text-[10px]">
                <Checkbox
                  checked={checked}
                  onCheckedChange={handleCheckedChange}
                  disabled={disabled || isSubmitting}
                  aria-label="Mark this candidate as checked"
                  className="size-3.5 rounded border-primary/30"
                />
                <span>Checked</span>
              </label>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex min-h-0 flex-1 flex-col p-4">
        <div className="review-graph grid min-h-0 flex-1 gap-4 lg:grid-cols-3">
          <ChunkNodePanel
            kind="source"
            nodeId={sourceChunk.id}
            displayLabel={sourceChunk.displayLabel}
            description={sourceChunk.description}
            text={sourceChunk.text}
            documentTitle={sourceDocumentTitle}
            hasFullDoc={Boolean(sourceDocument)}
            onOpenDoc={() => handleOpenDocument(true)}
          />

          <ChunkNodePanel
            kind="target"
            nodeId={targetChunk.id}
            displayLabel={targetChunk.displayLabel}
            description={targetChunk.description}
            text={targetChunk.text}
            documentTitle={targetDocumentTitle}
            hasFullDoc={Boolean(targetDocument)}
            onOpenDoc={() => handleOpenDocument(false)}
          />

          <div className="flex min-h-0 flex-col gap-4">
            <CandidateInsightPanel
              candidate={candidate}
              confidence={finalConfidence}
              editedRationale={editedRationale}
            />

            <aside className="review-note-panel min-h-[16rem] flex-1">
              <div className="review-note-header flex items-center gap-2.5">
                <div className="review-note-avatar flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-black" aria-hidden="true">
                  AI
                </div>
                <div>
                  <label htmlFor={noteId} className="text-xs font-bold text-foreground">
                    Reviewer Decision Note
                  </label>
                  <p className="text-[10px] font-semibold text-muted-foreground">
                    {readOnly
                      ? '이미 저장된 reviewer decision note입니다.'
                      : '이 candidate에 대한 approve/deny 근거를 남기면 commit 시 review graph와 memory update에 반영됩니다.'}
                  </p>
                </div>
              </div>

              <Textarea
                id={noteId}
                value={note}
                onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) => {
                  if (!readOnly) {
                    onNoteChange(event.target.value)
                  }
                }}
                placeholder={readOnly ? '저장된 review note가 없습니다.' : '승인 또는 반려 근거를 여기에 입력하세요... (선택 사항)'}
                className="review-note-textarea min-h-[8rem] rounded-lg border-primary/10 bg-background/40 p-2.5 text-xs leading-relaxed focus-visible:border-primary focus-visible:ring-primary"
                disabled={disabled || isSubmitting || readOnly}
              />

              {readOnly ? (
                <div className="rounded-lg border border-border/55 bg-muted/20 p-3 text-[10px] font-semibold text-muted-foreground">
                  <p>
                    Stored decision:{' '}
                    <span className="font-black text-foreground">{statusLabel}</span>
                  </p>
                  <p className="mt-1">
                    Reviewer:{' '}
                    <span className="font-black text-foreground">
                      {candidate.reviewer || 'unknown'}
                    </span>
                  </p>
                </div>
              ) : (
                <div className="review-decision-actions grid grid-cols-2 gap-2.5">
                  <Button
                    type="button"
                    variant="outline"
                    className="review-decision-button review-decision-button--deny h-9 rounded-lg border-destructive/20 bg-destructive/5 text-xs font-bold text-destructive hover:border-destructive hover:bg-destructive/10"
                    onClick={() => void handleDecision('no')}
                    disabled={disabled || isSubmitting}
                  >
                    <XIcon className="size-3.5 shrink-0" />
                    {submittingAction === 'no'
                      ? 'Staging'
                      : draftAction === 'no'
                        ? 'Deny Drafted'
                        : 'Stage Deny'}
                  </Button>
                  <Button
                    type="button"
                    className="review-decision-button review-decision-button--approve h-9 rounded-lg bg-chart-3 text-xs font-bold text-primary-foreground shadow-sm hover:bg-chart-3/95"
                    onClick={() => void handleDecision('yes')}
                    disabled={disabled || isSubmitting}
                  >
                    <CheckIcon className="size-3.5 shrink-0" />
                    {submittingAction === 'yes'
                      ? 'Staging'
                      : draftAction === 'yes'
                        ? 'Approve Drafted'
                        : 'Stage Approve'}
                  </Button>
                </div>
              )}
            </aside>
          </div>
        </div>
      </CardContent>

      <Dialog open={docModalOpen} onOpenChange={setDocModalOpen}>
        <DialogContent className="flex max-h-[85vh] flex-col overflow-hidden rounded-2xl border border-primary/10 bg-card/95 p-0 shadow-2xl backdrop-blur-md sm:max-w-4xl">
          <DialogHeader className="flex shrink-0 flex-row items-center gap-3 border-b border-border/45 bg-muted/15 p-6 pb-4.5">
            <div className="flex size-9.5 items-center justify-center rounded-xl border border-primary/20 bg-primary/10 text-primary">
              <BookOpen className="size-5" />
            </div>
            <div className="min-w-0 flex-1">
              <DialogTitle className="max-w-[28rem] truncate text-base font-extrabold tracking-tight text-foreground">
                {activeDocTitle}
              </DialogTitle>
              <DialogDescription className="mt-1 text-[10px] font-semibold text-muted-foreground/80">
                RAG ingested document context
              </DialogDescription>
            </div>
          </DialogHeader>
          <div className="min-h-0 flex-1 overflow-y-auto bg-background/25 p-6.5 font-mono text-[11px] leading-relaxed text-foreground whitespace-pre-wrap select-text">
            {activeDocContent}
          </div>
          <div className="flex shrink-0 justify-end border-t border-border/45 bg-muted/15 p-4 px-6.5">
            <Button
              type="button"
              onClick={() => setDocModalOpen(false)}
              className="h-8.5 rounded-lg bg-primary px-5 text-xs font-bold text-primary-foreground hover:bg-primary/95"
            >
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  )
}


function ChunkNodePanel({
  kind,
  nodeId,
  displayLabel,
  description,
  text,
  documentTitle,
  hasFullDoc,
  onOpenDoc,
}: ChunkNodePanelProps) {
  const [rawOpen, setRawOpen] = useState(false)
  const chunkDescription = description || '이 chunk에 대한 사람이 읽을 수 있는 설명이 아직 제공되지 않았습니다.'

  return (
    <section className={`review-node review-node--chunk review-node--${kind} border rounded-xl bg-card shadow-sm overflow-hidden flex flex-col min-h-[17.5rem]`}>
      
      <div className="review-node-header flex items-center justify-between p-3 bg-muted/20 border-b border-border/40">
        <div className="flex min-w-0 items-center gap-2">
          <div className={`review-node-icon flex size-7.5 items-center justify-center rounded-lg font-bold shadow-sm ${
            kind === 'source' 
              ? 'bg-primary/10 text-primary border border-primary/20 shadow-primary/5' 
              : 'bg-chart-2/10 text-chart-2 border border-chart-2/20 shadow-chart-2/5'
          }`}>
            <FileText className="size-3.5" aria-hidden="true" />
          </div>
          <div>
            <p className="review-node-kicker text-[8px] font-black text-muted-foreground uppercase tracking-widest leading-none">
              {kind === 'source' ? 'Source Chunk' : 'Target Chunk'}
            </p>
            <h4 className="mt-0.5 text-[11px] font-bold text-foreground max-w-[9rem] truncate" title={displayLabel}>
              {displayLabel}
            </h4>
            <p
              className="text-[8.5px] font-bold text-muted-foreground/75 mt-0.5 truncate max-w-[11rem] leading-none"
              title={documentTitle}
            >
              원본: {documentTitle}
            </p>
          </div>
        </div>
        
        <div className="flex shrink-0 flex-col items-end gap-1">
          <Badge variant="outline" className={`font-extrabold text-[8px] tracking-wide px-1.5 py-0.5 rounded-full ${
            kind === 'source'
              ? 'bg-primary/5 text-primary border-primary/20 shadow-sm'
              : 'bg-chart-2/5 text-chart-2 border-chart-2/20 shadow-sm'
          }`}>
            {kind === 'source' ? 'Source' : 'Target'}
          </Badge>
          {hasFullDoc && (
            <button
              type="button"
              onClick={onOpenDoc}
              className={cn(
                'flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[8px] font-extrabold tracking-wide shadow-sm transition-all hover:scale-[1.03]',
                kind === 'source'
                  ? 'bg-primary/10 text-primary border-primary/20 shadow-primary/5 hover:bg-primary/15'
                  : 'bg-chart-2/10 text-chart-2 border-chart-2/20 shadow-chart-2/5 hover:bg-chart-2/15'
              )}
            >
              <Sparkles className="size-2.5" />
              <span>Open Doc</span>
            </button>
          )}
        </div>
      </div>

      <div className="review-node-body p-3 flex-1 flex flex-col min-h-0 bg-background/30">
        <div
          className={cn(
            'flex min-h-0 flex-1 flex-col rounded-lg border bg-card/70 p-3 shadow-sm',
            kind === 'source'
              ? 'border-primary/15'
              : 'border-chart-2/15',
          )}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[8px] font-black uppercase tracking-widest text-muted-foreground">
                Chunk Description
              </p>
              <p className="mt-1 line-clamp-6 text-[11px] font-semibold leading-relaxed text-foreground/85">
                {chunkDescription}
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setRawOpen((open) => !open)}
              className={cn(
                'h-7 shrink-0 rounded-lg border bg-background/60 px-2 text-[10px] font-extrabold',
                kind === 'source'
                  ? 'border-primary/15 text-primary hover:bg-primary/5'
                  : 'border-chart-2/15 text-chart-2 hover:bg-chart-2/5',
              )}
            >
              <span className="flex items-center gap-1.5">
                <FileText className="size-3.5" aria-hidden="true" />
                {rawOpen ? '원문 닫기' : '원문 보기'}
              </span>
              <ChevronDown
                className={cn('size-3.5 transition-transform', rawOpen && 'rotate-180')}
                aria-hidden="true"
              />
            </Button>
          </div>

          <div className="mt-3 rounded-lg border border-border/55 bg-background/35 p-2.5">
            <p className="text-[8px] font-black uppercase tracking-widest text-muted-foreground">
              Original Document
            </p>
            <p className="mt-1 truncate text-[10px] font-extrabold text-foreground" title={documentTitle}>
              {documentTitle}
            </p>
            <p className="mt-1 break-all text-[8.5px] font-bold text-muted-foreground/70">
              Chunk ID: {nodeId}
            </p>
          </div>

          {rawOpen && (
            <div className="mt-3 flex min-h-0 flex-1 flex-col border-t border-border/45 pt-3">
              <ScrollArea className={cn(
                "review-document-scroll review-document-scroll--expanded border rounded-lg bg-card/65 select-text transition-all",
                kind === 'source'
                  ? 'border-primary/15'
                  : 'border-chart-2/15',
              )}>
                <RawTextViewer text={text} />
              </ScrollArea>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

type CandidateInsightPanelProps = {
  candidate: RelationshipCandidate
  confidence: number
  editedRationale: string
}

function CandidateInsightPanel({
  candidate,
  confidence,
  editedRationale,
}: CandidateInsightPanelProps) {
  const confidenceLabel = formatReviewCandidateConfidence(confidence)

  return (
    <section className="review-insight-panel flex min-h-[16rem] flex-1 flex-col overflow-hidden rounded-xl border border-primary/15 bg-card shadow-sm">
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-border/40 bg-muted/20 p-3">
        <div className="flex min-w-0 items-center gap-2">
          <div className="flex size-7.5 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary shadow-sm">
            <GitBranch className="size-3.5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="text-[8px] font-black uppercase tracking-widest text-muted-foreground">
              LLM Extraction Insight
            </p>
            <h4 className="mt-0.5 truncate text-[11px] font-bold text-foreground">
              관계 후보 추출 근거
            </h4>
          </div>
        </div>
        <Badge
          variant="outline"
          className={cn(
            'inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[8px] font-black',
            getReviewCandidateConfidenceBadgeClass(confidence),
          )}
        >
          {confidenceLabel}
        </Badge>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-3 p-3 text-[11px] leading-relaxed">
        <div className="rounded-lg border border-primary/10 bg-background/45 p-3">
          <p className="text-[8px] font-black uppercase tracking-widest text-primary">
            Rationale Summary
          </p>
          <p className="mt-1 whitespace-pre-wrap break-words font-semibold text-foreground/90">
            {editedRationale || 'No extraction rationale.'}
          </p>
        </div>

        <div className="min-h-0 flex-1 rounded-lg border border-border/60 bg-background/45 p-3">
          <p className="text-[8px] font-black uppercase tracking-widest text-muted-foreground">
            Evidence Text
          </p>
          <ScrollArea className="mt-1 h-[8.5rem]">
            <p className="whitespace-pre-wrap break-words pr-3 font-mono text-[10px] leading-relaxed text-muted-foreground">
              {candidate.evidence_text || 'Evidence text is not available.'}
            </p>
          </ScrollArea>
        </div>
      </div>
    </section>
  )
}

function formatMachineLabel(value: string) {
  return value
    .toLowerCase()
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function formatCandidateStatus(value: string) {
  const normalized = value.toLowerCase()
  if (normalized === 'pending_review') {
    return 'Review pending'
  }
  if (normalized === 'approved') {
    return 'Approved'
  }
  if (normalized === 'denied' || normalized === 'rejected') {
    return 'Denied'
  }
  return formatMachineLabel(value)
}

function getSourceChunk(candidate: RelationshipCandidate) {
  const displayLabel =
    candidate.source_chunk_label ??
    candidate.source_chunk_name ??
    getMetadataString(candidate, ['source_chunk_label', 'source_chunk_name', 'source_chunk_summary']) ??
    (candidate.source_chunk_id || candidate.source_node)
  return {
    documentLabel:
      getMetadataString(candidate, ['document_title', 'source_document_title', 'file_name']) ??
      candidate.job_id,
    displayLabel,
    description:
      candidate.source_chunk_description ??
      getMetadataString(candidate, ['source_chunk_description', 'source_chunk_summary']),
    id:
      getMetadataString(candidate, ['source_chunk_id']) ??
      (candidate.source_chunk_id || 'source-chunk'),
    text:
      candidate.source_chunk_text ??
      getMetadataString(candidate, ['source_chunk_text', 'source_text', 'chunk_text', 'source_chunk_summary']) ??
      (candidate.evidence_text || candidate.source_chunk_summary || 'Source chunk context is not available from the API response.'),
  }
}

function getTargetChunk(candidate: RelationshipCandidate) {
  const displayLabel =
    candidate.target_chunk_label ??
    candidate.target_chunk_name ??
    getMetadataString(candidate, ['target_chunk_label', 'target_chunk_name', 'target_chunk_summary']) ??
    candidate.target_node
  return {
    documentLabel:
      getMetadataString(candidate, ['target_document_title', 'document_title', 'file_name']) ??
      candidate.job_id,
    displayLabel,
    description:
      candidate.target_chunk_description ??
      getMetadataString(candidate, ['target_chunk_description', 'target_chunk_summary']),
    id:
      candidate.target_chunk_id ??
      getMetadataString(candidate, ['target_chunk_id', 'target_chunk_node_id', 'related_chunk_id']) ??
      candidate.target_node,
    text:
      candidate.target_chunk_text ??
      getMetadataString(candidate, ['target_chunk_text', 'target_text', 'matched_chunk_text', 'target_chunk_summary']) ??
      candidate.target_chunk_summary ??
      candidate.target_chunk_description ??
      'Target chunk context is not available from the API response.',
  }
}

function getChunkDocumentTitle({
  candidate,
  chunkDocumentLabel,
  document,
  fallbackTitle,
  kind,
}: {
  candidate: RelationshipCandidate
  chunkDocumentLabel: string
  document: RagDocument | null
  fallbackTitle: string | null
  kind: 'source' | 'target'
}) {
  const sourceCandidates = [
    getMetadataString(candidate, ['source_document_title', 'document_title', 'source_title', 'file_name']),
    document?.source_title,
    document?.file_name,
    fallbackTitle,
    chunkDocumentLabel,
  ]
  const targetCandidates = [
    getMetadataString(candidate, ['target_document_title', 'target_source_title', 'target_file_name']),
    document?.source_title,
    document?.file_name,
    getMetadataString(candidate, ['document_title', 'source_title', 'file_name']),
    fallbackTitle,
    chunkDocumentLabel,
  ]
  return firstReadableDisplayValue(kind === 'source' ? sourceCandidates : targetCandidates) ??
    (kind === 'source' ? 'Source document' : 'Target document')
}

function firstReadableDisplayValue(values: Array<string | null | undefined>) {
  for (const value of values) {
    const normalized = normalizeDisplayValue(value)
    if (normalized && !isUuidLike(normalized)) {
      return stripKnownExtension(normalized)
    }
  }

  return null
}

function normalizeDisplayValue(value: string | null | undefined) {
  const trimmed = value?.trim()
  if (!trimmed) {
    return null
  }

  return trimmed.split('/').pop()?.normalize('NFC') || trimmed.normalize('NFC')
}

function stripKnownExtension(value: string) {
  return value.replace(/\.(toon|md|markdown|txt|json|pdf|docx?)$/i, '')
}

function isUuidLike(value: string) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
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
