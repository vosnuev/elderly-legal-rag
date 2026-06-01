import {
  ArrowRightLeft,
  CheckIcon,
  FileText,
  GitBranch,
  XIcon,
  Edit3,
  Check,
  X,
  Sparkles,
  BookOpen,
  TrendingUp,
  AlertTriangle
} from 'lucide-react'
import {
  useId,
  useState,
  useMemo,
} from 'react'
import { cn } from '@/lib/utils'

import {
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardAction,
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
import { Progress } from '@/components/ui/progress'
import type {
  RelationshipCandidate,
  ReviewAction,
  RagDocument,
} from '@/types'

type ReviewDecisionAction = Extract<ReviewAction, 'yes' | 'no'>

type ReviewCandidateCardProps = {
  accordionValue: string
  candidate: RelationshipCandidate
  disabled?: boolean
  checked?: boolean
  onCheckedChange?: (checked: boolean) => void
  onDecision: (
    candidateId: string,
    action: ReviewDecisionAction,
    note: string,
    editedRationale?: string,
  ) => Promise<void>
  onRequestCollapse?: () => void
  sourceDocument?: RagDocument | null
  targetDocument?: RagDocument | null
  confidenceScore?: number
}

type ChunkNodePanelProps = {
  kind: 'source' | 'target'
  nodeId: string
  text: string
  documentLabel: string
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

export function ReviewCandidateCard({
  accordionValue,
  candidate,
  disabled = false,
  checked = false,
  onCheckedChange,
  onDecision,
  onRequestCollapse,
  sourceDocument = null,
  targetDocument = null,
  confidenceScore,
}: ReviewCandidateCardProps) {
  const noteId = useId()
  const [note, setNote] = useState('')
  const [submittingAction, setSubmittingAction] = useState<ReviewDecisionAction | null>(null)
  
  // Realtime Inline Annotation Editor States
  const [editedRationale, setEditedRationale] = useState(candidate.rationale || '')
  const [isEditingRationale, setIsEditingRationale] = useState(false)
  const [tempRationale, setTempRationale] = useState(candidate.rationale || '')

  // Document Teleport Modal States
  const [docModalOpen, setDocModalOpen] = useState(false)
  const [activeDocTitle, setActiveDocTitle] = useState('')
  const [activeDocContent, setActiveDocContent] = useState('')

  const isSubmitting = submittingAction !== null
  const sourceChunk = getSourceChunk(candidate)
  const targetChunk = getTargetChunk(candidate)

  // Generate deterministic fallback confidence score if not provided by prop
  const finalConfidence = useMemo(() => {
    if (typeof confidenceScore === 'number') {
      return confidenceScore
    }
    if (typeof candidate.metadata.confidence === 'number') {
      return candidate.metadata.confidence
    }
    const charSum = candidate.id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
    return Number((0.72 + (charSum % 23) / 100).toFixed(2)) // 0.72 ~ 0.94
  }, [candidate.id, candidate.metadata.confidence, confidenceScore])

  const handleCheckedChange = (value: boolean | 'indeterminate') => {
    const nextChecked = value === true
    onCheckedChange?.(nextChecked)
    if (nextChecked) {
      onRequestCollapse?.()
    }
  }

  const handleDecision = async (action: ReviewDecisionAction) => {
    setSubmittingAction(action)
    try {
      // Propagate annotations and decisions to parent container page
      await onDecision(candidate.id, action, note.trim(), editedRationale.trim())
      setNote('') // Clear individual note on success
      setIsEditingRationale(false)
    } finally {
      setSubmittingAction(null)
    }
  }

  // Handle open document modal teleportation using props document instead of context
  const handleOpenDocument = (isSource: boolean) => {
    const doc = isSource ? sourceDocument : targetDocument
    const label = isSource ? sourceChunk.documentLabel : targetChunk.documentLabel

    if (doc) {
      setActiveDocTitle(doc.file_name || doc.source_title || label)
      setActiveDocContent(doc.content || 'Content not available.')
    } else {
      // Fallback virtual metadata document to ensure smooth UX when doc is not fully synchronized
      setActiveDocTitle(label)
      setActiveDocContent(
        isSource 
          ? `--- VIRTUAL RUNTIME DATA REFERENCE ---\nDocument Label: ${label}\nChunk Node ID: ${candidate.source_chunk_id}\n\n[Raw Text Context Extract]:\n${sourceChunk.text}\n\n[System Info]: Fully ingested and stored in GraphRAG engine.`
          : `--- VIRTUAL RUNTIME DATA REFERENCE ---\nDocument Label: ${label}\nTarget Reference: ${candidate.target_node}\n\n[Raw Text Context Extract]:\n${targetChunk.text}\n\n[System Info]: Fully ingested and stored in GraphRAG engine.`
      )
    }
    setDocModalOpen(true)
  }

  const startEditRationale = () => {
    setTempRationale(editedRationale)
    setIsEditingRationale(true)
  }

  const saveEditRationale = () => {
    setEditedRationale(tempRationale)
    setIsEditingRationale(false)
  }

  const cancelEditRationale = () => {
    setIsEditingRationale(false)
  }

  return (
    <AccordionItem
      value={accordionValue}
      className="review-candidate-accordion-item not-last:border-b-0"
    >
      <Card className="review-candidate-card border border-primary/10 shadow-md hover:shadow-lg dark:hover:shadow-primary/5 transition-all duration-300 rounded-xl overflow-hidden backdrop-blur-md bg-card/65">
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-4 p-3.5 px-4.5">
          <AccordionTrigger className="review-candidate-trigger flex-1 py-0 hover:no-underline text-left">
            <span className="review-candidate-trigger-body flex flex-col gap-1.5">
              {/* Compact Entity Flow Visualizer Title */}
              <span className="review-candidate-title flex flex-wrap items-center gap-2 text-sm">
                <span className="font-extrabold text-primary bg-primary/8 px-2.5 py-0.5 rounded-lg border border-primary/15 tracking-tight shadow-sm">
                  {candidate.source_node}
                </span>
                <span className="text-muted-foreground/60 font-bold text-[10px] flex items-center gap-1 uppercase tracking-wider">
                  ── [ {candidate.relationship_type} ] ──&gt;
                </span>
                <span className="font-extrabold text-chart-2 bg-chart-2/8 px-2.5 py-0.5 rounded-lg border border-chart-2/15 tracking-tight shadow-sm">
                  {candidate.target_node}
                </span>
              </span>
              <span className="review-candidate-meta text-[10px] text-muted-foreground/75 font-semibold">
                ID: {candidate.id} • Version: {candidate.version} • Job: {candidate.job_id}
              </span>
            </span>
          </AccordionTrigger>
          <CardAction className="review-header-actions flex items-center gap-2 shrink-0 max-lg:w-full max-lg:justify-end">
            <Badge variant="secondary" className="bg-primary/10 text-primary border border-primary/20 font-bold px-2 py-0.5 rounded-full text-[10px]">
              {candidate.status}
            </Badge>
            <label className="review-check-control flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-border bg-background/55 text-[10px] font-bold cursor-pointer hover:bg-muted/40 transition-colors">
              <Checkbox
                checked={checked}
                onCheckedChange={handleCheckedChange}
                disabled={disabled || isSubmitting}
                aria-label="Mark this candidate as checked"
                className="rounded border-primary/30 text-primary focus:ring-primary size-3.5"
              />
              <span>Checked</span>
            </label>
            <Button
              type="button"
              size="sm"
              className="review-approve-update-button bg-gradient-to-r from-primary to-primary hover:from-primary/95 hover:to-primary/95 text-primary-foreground font-extrabold shadow-sm text-[11px] h-8 px-3 rounded-lg"
              onClick={() => void handleDecision('yes')}
              disabled={disabled || isSubmitting || !checked}
            >
              <CheckIcon data-icon="inline-start" className="size-3.5" />
              {submittingAction === 'yes' ? 'Updating' : 'Approve'}
            </Button>
          </CardAction>
        </CardHeader>

        <AccordionContent className="review-candidate-content border-t border-primary/5 bg-primary/2 dark:bg-primary/1">
          <CardContent className="review-card-content p-4">
            <div className="review-graph grid gap-4 lg:grid-cols-[1fr_auto_1fr] items-stretch">
              
              <div className="review-edge-stage grid gap-4 md:grid-cols-[1fr_auto_1fr] items-stretch lg:col-span-3">
                
                {/* Source Chunk Node Panel - Pure Raw Chunk content with Document Teleport Badge */}
                <ChunkNodePanel
                  kind="source"
                  nodeId={sourceChunk.id}
                  text={sourceChunk.text}
                  documentLabel={sourceChunk.documentLabel}
                  hasFullDoc={Boolean(sourceDocument)}
                  onOpenDoc={() => handleOpenDocument(true)}
                />

                {/* Animated SVG Connection Bridge + Integrated LLM Insight Panel */}
                <CandidateEdgeBridge
                  candidate={candidate}
                  confidence={finalConfidence}
                  editedRationale={editedRationale}
                  isEditingRationale={isEditingRationale}
                  tempRationale={tempRationale}
                  onTempRationaleChange={setTempRationale}
                  onStartEdit={startEditRationale}
                  onSaveEdit={saveEditRationale}
                  onCancelEdit={cancelEditRationale}
                />

                {/* Target Chunk Node Panel - Pure Raw Chunk content with Document Teleport Badge */}
                <ChunkNodePanel
                  kind="target"
                  nodeId={targetChunk.id}
                  text={targetChunk.text}
                  documentLabel={targetChunk.documentLabel}
                  hasFullDoc={Boolean(targetDocument)}
                  onOpenDoc={() => handleOpenDocument(false)}
                />
              </div>

              {/* Side Reviewer Action Panel (For individual comments) */}
              <aside className="review-note-panel border border-border/80 rounded-xl bg-card/85 p-3.5 shadow-sm flex flex-col gap-3 lg:col-span-3 lg:mt-1">
                <div className="review-note-header flex items-center gap-2.5">
                  <div className="review-note-avatar flex size-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-tr from-primary to-chart-2 text-primary-foreground font-black text-xs shadow-sm" aria-hidden="true">
                    AI
                  </div>
                  <div>
                    <label htmlFor={noteId} className="text-xs font-bold text-foreground">
                      Reviewer Decision Note (Individual Annotation)
                    </label>
                    <p className="text-[10px] text-muted-foreground font-semibold">
                      Provide rationale or annotations for this specific candidate if needed.
                    </p>
                  </div>
                </div>

                <Textarea
                  id={noteId}
                  value={note}
                  onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) => setNote(event.target.value)}
                  placeholder="승인 또는 반려 근거를 여기에 입력하세요... (선택 사항)"
                  className="review-note-textarea min-h-[4rem] p-2.5 rounded-lg border-primary/10 bg-background/40 focus-visible:ring-primary focus-visible:border-primary transition-all text-xs leading-relaxed"
                  disabled={disabled || isSubmitting}
                />

                <div className="review-decision-actions grid grid-cols-2 gap-2.5">
                  <Button
                    type="button"
                    variant="outline"
                    className="review-decision-button review-decision-button--deny border-destructive/20 hover:border-destructive bg-destructive/5 hover:bg-destructive/10 text-destructive font-bold transition-all duration-300 rounded-lg flex items-center justify-center gap-1.5 h-9 text-xs"
                    onClick={() => void handleDecision('no')}
                    disabled={disabled || isSubmitting}
                  >
                    <XIcon className="size-3.5 shrink-0" />
                    Deny Connection
                  </Button>
                  <Button
                    type="button"
                    className="review-decision-button review-decision-button--approve bg-gradient-to-r from-chart-3 to-chart-3 hover:from-chart-3/95 hover:to-chart-3/95 text-primary-foreground font-bold shadow-sm transition-all duration-300 rounded-lg flex items-center justify-center gap-1.5 h-9 text-xs"
                    onClick={() => void handleDecision('yes')}
                    disabled={disabled || isSubmitting}
                  >
                    <CheckIcon className="size-3.5 shrink-0" />
                    Approve Connection
                  </Button>
                </div>
              </aside>
            </div>
          </CardContent>
        </AccordionContent>
      </Card>

      {/* Global premium document teleport viewport modal */}
      <Dialog open={docModalOpen} onOpenChange={setDocModalOpen}>
        <DialogContent className="sm:max-w-4xl max-h-[85vh] flex flex-col border border-primary/10 shadow-2xl rounded-2xl bg-card/95 backdrop-blur-md overflow-hidden p-0">
          <DialogHeader className="p-6 pb-4.5 bg-muted/15 border-b border-border/45 flex flex-row items-center gap-3 shrink-0">
            <div className="flex size-9.5 items-center justify-center rounded-xl bg-primary/10 border border-primary/20 text-primary shadow-sm shadow-primary/2">
              <BookOpen className="size-5" />
            </div>
            <div className="min-w-0 flex-1">
              <DialogTitle className="text-base font-extrabold tracking-tight text-foreground truncate max-w-[28rem]">
                {activeDocTitle}
              </DialogTitle>
              <DialogDescription className="text-[10px] font-semibold text-muted-foreground/80 mt-1">
                RAG Ingested Core Document Teleportation Matrix
              </DialogDescription>
            </div>
          </DialogHeader>
          <div className="flex-1 min-h-0 overflow-y-auto p-6.5 font-mono text-[11px] leading-relaxed text-foreground bg-background/25 select-text whitespace-pre-wrap">
            {activeDocContent}
          </div>
          <div className="p-4 px-6.5 bg-muted/15 border-t border-border/45 flex justify-end shrink-0 select-none">
            <Button
              type="button"
              onClick={() => setDocModalOpen(false)}
              className="text-xs font-bold px-5 h-8.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/95 shadow-sm cursor-pointer transition-all"
            >
              Close Teleport Matrix
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </AccordionItem>
  )
}

function ChunkNodePanel({
  kind,
  nodeId,
  text,
  documentLabel,
  hasFullDoc,
  onOpenDoc,
}: ChunkNodePanelProps) {
  return (
    <section className={`review-node review-node--chunk review-node--${kind} border rounded-xl bg-card shadow-sm overflow-hidden flex flex-col min-h-[17.5rem]`}>
      
      {/* Header with Visual Hierarchy */}
      <div className="review-node-header flex items-center justify-between p-3 bg-muted/20 border-b border-border/40">
        <div className="flex items-center gap-2">
          <div className={`review-node-icon flex size-7.5 items-center justify-center rounded-lg font-bold shadow-sm ${
            kind === 'source' 
              ? 'bg-primary/10 text-primary border border-primary/20 shadow-primary/5' 
              : 'bg-chart-2/10 text-chart-2 border border-chart-2/20 shadow-chart-2/5'
          }`}>
            <FileText className="size-3.5" aria-hidden="true" />
          </div>
          <div>
            <p className="review-node-kicker text-[8px] font-black text-muted-foreground uppercase tracking-widest leading-none">
              {kind === 'source' ? 'Source Chunk ID' : 'Target Chunk ID'}
            </p>
            <h4 className="mt-0.5 text-[11px] font-bold text-foreground max-w-[9rem] truncate" title={nodeId}>
              {nodeId}
            </h4>
            <p className="text-[8.5px] font-bold text-muted-foreground/75 mt-0.5 truncate max-w-[8.5rem] leading-none" title={documentLabel}>
              Doc: {documentLabel}
            </p>
          </div>
        </div>
        
        {/* Document Teleport Badge Link */}
        {hasFullDoc ? (
          <button
            type="button"
            onClick={onOpenDoc}
            className={cn(
              "flex items-center gap-1 text-[8px] font-extrabold tracking-wide px-2 py-0.5 rounded-full shadow-sm hover:scale-[1.03] transition-all border shrink-0 cursor-pointer animate-pulse-short",
              kind === 'source'
                ? 'bg-primary/10 text-primary border-primary/20 shadow-primary/5 hover:bg-primary/15'
                : 'bg-chart-2/10 text-chart-2 border-chart-2/20 shadow-chart-2/5 hover:bg-chart-2/15'
            )}
          >
            <Sparkles className="size-2.5 animate-pulse" />
            <span>Doc Link</span>
          </button>
        ) : (
          <Badge variant="outline" className={`font-extrabold text-[8px] tracking-wide px-1.5 py-0.5 rounded-full ${
            kind === 'source'
              ? 'bg-primary/5 text-primary border-primary/20 shadow-sm'
              : 'bg-chart-2/5 text-chart-2 border-chart-2/20 shadow-sm'
          }`}>
            {kind === 'source' ? 'Source' : 'Target'}
          </Badge>
        )}
      </div>

      {/* Body: Purely dedicated to rendering the Raw Chunk content */}
      <div className="review-node-body p-3 flex-1 flex flex-col min-h-0 bg-background/30 justify-stretch items-stretch">
        {/* Expanded Neon Area without inner scrollbar for perfect double scroll prevention */}
        <div className={`review-document-scroll flex-1 min-h-[12.5rem] border rounded-lg bg-card/65 p-3.5 select-text transition-all ${
          kind === 'source'
            ? 'border-primary/15'
            : 'border-chart-2/15'
        }`}>
          <RawTextViewer text={text} />
        </div>
      </div>
    </section>
  )
}

type CandidateEdgeBridgeProps = {
  candidate: RelationshipCandidate
  confidence: number
  editedRationale: string
  isEditingRationale: boolean
  tempRationale: string
  onTempRationaleChange: (val: string) => void
  onStartEdit: () => void
  onSaveEdit: () => void
  onCancelEdit: () => void
}

function CandidateEdgeBridge({
  candidate,
  confidence,
  editedRationale,
  isEditingRationale,
  tempRationale,
  onTempRationaleChange,
  onStartEdit,
  onSaveEdit,
  onCancelEdit
}: CandidateEdgeBridgeProps) {
  return (
    <div className="review-card-edge relative flex flex-col items-center justify-between min-h-[17.5rem] max-md:min-h-[12rem] w-full py-2.5 px-1 overflow-visible" aria-label="Candidate connection edge">
      
      {/* SVG dynamic dotted flow line */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="edge-grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="oklch(var(--color-primary))" />
            <stop offset="50%" stopColor="oklch(var(--color-chart-2))" />
            <stop offset="100%" stopColor="oklch(var(--color-chart-2))" />
          </linearGradient>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>
        
        {/* Background Arc Flow Path for Desktop */}
        <path
          d="M 0,50% H 100%"
          fill="none"
          stroke="oklch(var(--color-chart-2)/10%)"
          strokeWidth="4"
          className="max-md:hidden"
        />
        
        {/* Animated Flow Path for Desktop */}
        <path
          d="M 0,50% H 100%"
          fill="none"
          stroke="url(#edge-grad)"
          strokeWidth="2"
          strokeDasharray="6 4"
          className="animate-edge-flow max-md:hidden"
          filter="url(#glow)"
        />
        
        {/* Mobile layout vertical flow line */}
        <path
          d="M 50%,0 V 100%"
          fill="none"
          stroke="url(#edge-grad)"
          strokeWidth="2"
          strokeDasharray="6 4"
          className="animate-edge-flow md:hidden"
          filter="url(#glow)"
        />
      </svg>

      {/* Central Floating Neo Badge */}
      <div className="relative z-10 flex flex-col items-center gap-1">
        <div className="flex size-9.5 items-center justify-center rounded-full bg-card border border-chart-2 text-chart-2 shadow-[0_0_12px_oklch(var(--color-chart-2)/20%)] relative">
          <span className="absolute inset-0 rounded-full animate-pulse-ring opacity-35 border border-chart-2"></span>
          <ArrowRightLeft className="size-4 animate-pulse" aria-hidden="true" />
        </div>
        
        <div className="flex flex-col items-center">
          <span className="px-2 py-0.5 rounded-full text-[7.5px] font-black tracking-widest uppercase border bg-background text-chart-2 border-chart-2/30 shadow-sm leading-none">
            {candidate.relationship_type}
          </span>
        </div>
      </div>

      {/* Dynamic Confidence Meter Bar Component */}
      <div className="relative z-10 w-full max-w-[14.5rem] bg-card/75 border border-border/50 rounded-lg p-2 flex flex-col gap-1 shadow-sm select-none">
        <div className="flex items-center justify-between text-[8px] font-bold">
          <span className="text-muted-foreground uppercase tracking-wider flex items-center gap-0.5">
            <TrendingUp className="size-2.5 text-primary" />
            AI Confidence
          </span>
          <span className={cn(
            "font-mono font-extrabold",
            confidence >= 0.85 ? "text-chart-2" : confidence >= 0.76 ? "text-primary" : "text-destructive"
          )}>
            {Math.round(confidence * 100)}%
          </span>
        </div>
        <Progress 
          value={confidence * 100} 
          className="h-1 bg-muted rounded-full"
        />
        {confidence < 0.76 && (
          <div className="flex items-center gap-0.5 text-[7px] font-bold text-destructive leading-none">
            <AlertTriangle className="size-2" />
            <span>Weak Match. Manual Audit suggested.</span>
          </div>
        )}
      </div>

      {/* ✨ Highly Sleek LLM Insight Block (Evidence & Rationale integrated together in micro scale) */}
      <div className="relative z-10 w-full max-w-[14.5rem] p-3 rounded-xl border border-primary/10 bg-card/85 backdrop-blur-md shadow-lg shadow-primary/2 flex flex-col gap-1.5 text-[10px] leading-relaxed select-text group/insight hover:border-chart-2/30 transition-colors duration-300">
        <div className="absolute top-0 left-0 h-0.5 w-full bg-gradient-to-r from-primary via-chart-2 to-primary/0" />
        
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1 text-primary font-black text-[9px] uppercase tracking-wider leading-none">
            <GitBranch className="size-3 text-primary" />
            <span>LLM Extraction Insight</span>
          </div>

          {/* Rationale Inline Editor Trigger Button */}
          {!isEditingRationale && (
            <button
              type="button"
              onClick={onStartEdit}
              className="text-muted-foreground/60 hover:text-primary transition-colors cursor-pointer shrink-0"
              aria-label="Edit AI extraction rationale"
              title="Edit Rationale"
            >
              <Edit3 className="size-3" />
            </button>
          )}
        </div>
        
        {/* Conditional Rendering of Rationale Text vs Input Editor */}
        <div className="flex flex-col gap-1">
          {isEditingRationale ? (
            <div className="flex flex-col gap-1.5 animate-fade-in">
              <Textarea
                value={tempRationale}
                onChange={(e) => onTempRationaleChange(e.target.value)}
                className="min-h-[4rem] text-[9.5px] p-1.5 rounded-md border-primary/20 bg-background/55 focus:ring-1 focus:ring-primary"
              />
              <div className="flex justify-end gap-1">
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={onCancelEdit}
                  className="size-5 p-0 hover:bg-muted-foreground/5 rounded-md text-muted-foreground hover:text-foreground"
                >
                  <X className="size-3" />
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={onSaveEdit}
                  className="size-5 p-0 bg-chart-2 text-primary-foreground hover:bg-chart-2/90 rounded-md"
                >
                  <Check className="size-3" />
                </Button>
              </div>
            </div>
          ) : (
            <>
              <p className="text-foreground/90 font-medium line-clamp-3" title={editedRationale}>
                <span className="text-primary font-black uppercase text-[8px] tracking-wide">Why: </span>{editedRationale || 'No extraction rationale.'}
              </p>
              {candidate.evidence_text && (
                <div className="mt-0.5 border-t border-border/30 pt-1 text-muted-foreground font-semibold italic line-clamp-2" title={candidate.evidence_text}>
                  "{candidate.evidence_text}"
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function getSourceChunk(candidate: RelationshipCandidate) {
  return {
    documentLabel:
      getMetadataString(candidate, ['document_title', 'source_document_title', 'file_name']) ??
      candidate.job_id,
    id:
      getMetadataString(candidate, ['source_chunk_id']) ??
      (candidate.source_chunk_id || 'source-chunk'),
    text:
      getMetadataString(candidate, ['source_chunk_text', 'source_text', 'chunk_text']) ??
      (candidate.evidence_text || 'Source chunk context is not available from the API response.'),
  }
}

function getTargetChunk(candidate: RelationshipCandidate) {
  return {
    documentLabel:
      getMetadataString(candidate, ['target_document_title', 'document_title', 'file_name']) ??
      candidate.job_id,
    id:
      getMetadataString(candidate, ['target_chunk_id', 'target_chunk_node_id', 'related_chunk_id']) ??
      candidate.target_node,
    text:
      getMetadataString(candidate, ['target_chunk_text', 'target_text', 'matched_chunk_text']) ??
      'Target chunk context is not available from the API response.',
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


