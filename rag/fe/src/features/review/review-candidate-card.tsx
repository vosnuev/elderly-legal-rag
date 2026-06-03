import {
  ArrowRightLeft,
  CheckIcon,
  FileText,
  GitBranch,
  XIcon,
} from 'lucide-react'
import {
  useId,
  useState,
} from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

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
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import type {
  RelationshipCandidate,
  ReviewAction,
} from '@/types'

const markdownPlugins = [remarkGfm]

type ReviewDecisionAction = Extract<ReviewAction, 'yes' | 'no'>

type ReviewCandidateCardProps = {
  accordionValue: string
  candidate: RelationshipCandidate
  disabled?: boolean
  onDecision: (
    candidateId: string,
    action: ReviewDecisionAction,
    note: string,
  ) => Promise<void>
  onRequestCollapse?: () => void
}

type ChunkNodePanelProps = {
  documentLabel: string
  kind: 'source' | 'target'
  nodeId: string
  text: string
}

export function ReviewCandidateCard({
  accordionValue,
  candidate,
  disabled = false,
  onDecision,
  onRequestCollapse,
}: ReviewCandidateCardProps) {
  const noteId = useId()
  const [note, setNote] = useState('')
  const [checked, setChecked] = useState(false)
  const [submittingAction, setSubmittingAction] = useState<ReviewDecisionAction | null>(null)
  const isSubmitting = submittingAction !== null
  const sourceChunk = getSourceChunk(candidate)
  const targetChunk = getTargetChunk(candidate)

  const handleCheckedChange = (value: boolean | 'indeterminate') => {
    const nextChecked = value === true
    setChecked(nextChecked)
    if (nextChecked) {
      onRequestCollapse?.()
    }
  }

  const handleDecision = async (action: ReviewDecisionAction) => {
    setSubmittingAction(action)
    try {
      await onDecision(candidate.id, action, note.trim())
    } finally {
      setSubmittingAction(null)
    }
  }

  return (
    <AccordionItem
      value={accordionValue}
      className="review-candidate-accordion-item not-last:border-b-0"
    >
      <Card className="review-candidate-card">
        <CardHeader>
          <AccordionTrigger className="review-candidate-trigger border-0 py-0 hover:no-underline">
            <span className="review-candidate-trigger-body">
              <span className="review-candidate-title">
                <span>{candidate.source_node}</span>
                <Badge variant="outline">{candidate.relationship_type}</Badge>
                <span>{candidate.target_node}</span>
              </span>
              <span className="review-candidate-meta">
                {candidate.id} - job {candidate.job_id} - version {candidate.version}
              </span>
            </span>
          </AccordionTrigger>
          <CardAction className="review-header-actions col-start-1 row-start-2 row-span-1 justify-self-start lg:col-start-2 lg:row-start-1 lg:justify-self-end">
            <Badge variant="secondary">{candidate.status}</Badge>
            <label className="review-check-control">
              <Checkbox
                checked={checked}
                onCheckedChange={handleCheckedChange}
                disabled={disabled || isSubmitting}
                aria-label="Mark this candidate as checked"
              />
              <span>Checked</span>
            </label>
            <Button
              type="button"
              size="sm"
              className="review-approve-update-button"
              onClick={() => void handleDecision('yes')}
              disabled={disabled || isSubmitting || !checked}
            >
              <CheckIcon data-icon="inline-start" />
              {submittingAction === 'yes' ? 'Updating' : 'Approve update'}
            </Button>
          </CardAction>
        </CardHeader>

        <AccordionContent className="review-candidate-content">
          <CardContent className="review-card-content">
            <div className="review-graph">
              <div className="review-edge-stage">
                <ChunkNodePanel
                  kind="source"
                  nodeId={sourceChunk.id}
                  documentLabel={sourceChunk.documentLabel}
                  text={sourceChunk.text}
                />

                <CandidateEdgeBridge candidate={candidate} />

                <ChunkNodePanel
                  kind="target"
                  nodeId={targetChunk.id}
                  documentLabel={targetChunk.documentLabel}
                  text={targetChunk.text}
                />

                <div className="review-edge-details">
                  <div className="review-evidence-block">
                    <div className="review-block-title">
                      <FileText aria-hidden="true" />
                      <p>RAG Builder Evidence</p>
                    </div>
                    <p className="text-sm leading-6">
                      {candidate.evidence_text || 'No evidence text provided.'}
                    </p>
                  </div>

                  <div className="review-evidence-block">
                    <div className="review-block-title">
                      <GitBranch aria-hidden="true" />
                      <p>LLM Rationale</p>
                    </div>
                    <p className="text-sm leading-6">{candidate.rationale || 'No rationale provided.'}</p>
                  </div>
                </div>
              </div>

              <aside className="review-note-panel">
                <div className="review-note-header">
                  <div className="review-note-avatar" aria-hidden="true">
                    R
                  </div>
                  <div>
                    <label htmlFor={noteId} className="text-sm font-medium">
                      Reviewer note
                    </label>
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">
                      Decision comment
                    </p>
                  </div>
                </div>

                <Textarea
                  id={noteId}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="승인 또는 반려 근거를 남기세요."
                  className="review-note-textarea"
                  disabled={disabled || isSubmitting}
                />

                <div className="review-decision-actions">
                  <Button
                    type="button"
                    variant="outline"
                    className="review-decision-button review-decision-button--deny"
                    onClick={() => void handleDecision('no')}
                    disabled={disabled || isSubmitting}
                  >
                    <XIcon data-icon="inline-start" />
                    {submittingAction === 'no' ? 'Denying' : 'Deny'}
                  </Button>
                  <Button
                    type="button"
                    className="review-decision-button review-decision-button--approve"
                    onClick={() => void handleDecision('yes')}
                    disabled={disabled || isSubmitting}
                  >
                    <CheckIcon data-icon="inline-start" />
                    {submittingAction === 'yes' ? 'Approving' : 'Approve'}
                  </Button>
                </div>
              </aside>
            </div>
          </CardContent>
        </AccordionContent>
      </Card>
    </AccordionItem>
  )
}

function ChunkNodePanel({
  documentLabel,
  kind,
  nodeId,
  text,
}: ChunkNodePanelProps) {
  return (
    <section className={`review-node review-node--chunk review-node--${kind}`}>
      <div className="review-node-header">
        <div className="review-node-title-row">
          <div className="review-node-icon review-node-icon--chunk">
            <FileText aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="review-node-kicker">
              {kind === 'source' ? 'Source chunk' : 'Target chunk'}
            </p>
          </div>
        </div>
        <Badge variant="outline" className="review-node-id-badge" title={nodeId}>
          {nodeId}
        </Badge>
      </div>

      <Separator />

      <div className="review-node-body">
        <div className="review-document-block">
          <div className="review-document-heading">
            <p className="text-xs font-medium text-muted-foreground">Document</p>
            <p className="break-words text-sm">{documentLabel}</p>
          </div>
          <ScrollArea className="review-document-scroll">
            <MarkdownDocument text={text} />
          </ScrollArea>
        </div>
      </div>
    </section>
  )
}

function MarkdownDocument({ text }: { text: string }) {
  return (
    <div className="review-markdown">
      <ReactMarkdown remarkPlugins={markdownPlugins}>{text}</ReactMarkdown>
    </div>
  )
}

function CandidateEdgeBridge({ candidate }: { candidate: RelationshipCandidate }) {
  return (
    <div className="review-card-edge" aria-label="Candidate connection edge">
      <span className="review-card-edge-line" />
      <span className="review-card-edge-badge">
        <ArrowRightLeft aria-hidden="true" />
        {candidate.relationship_type}
      </span>
      <span className="review-card-edge-state">Candidate connection</span>
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
