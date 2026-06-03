export interface CreateDocumentIngestJobRequest {
  file_name: string
  content: string
  content_type?: string | null
}

export interface IngestStageResult {
  phase?: string
  stage?: string
  status: string
  message: string
  path?: string | null
  error?: string | null
  recorded_at?: string | null
}

export interface GraphTaskSnapshot {
  task_id: string
  kind: 'build' | 'review' | 'construction' | 'review_action' | string
  status: 'queued' | 'running' | 'succeeded' | 'failed' | string
  idempotency_key: string
  submitted_at: string
  started_at?: string | null
  finished_at?: string | null
  error?: string | null
}

export interface FileIngestStatusResponse {
  job_id: string
  file_name: string
  current_phase?: string
  current_stage?: string
  completed: boolean
  stages: IngestStageResult[]
  created_at?: string | null
  updated_at?: string | null
  completed_at?: string | null
  warning?: string | null
  document_id?: string | null
  chunk_count?: number
  candidate_count?: number
  pending_review_count?: number
  current_task?: GraphTaskSnapshot | null
}

export interface RagDocument {
  content: string
  source_title: string
  file_name: string
  file_type: string
  created_at?: string | null
  indexed_at?: string | null
  updated_at?: string | null
  document_id?: string | null
  job_id?: string | null
  location?: string | null
  url?: string | null
  score?: number
}

export interface ReviewCandidateResponse {
  columns?: string[]
  rows?: unknown[]
  row_count?: number
  elapsed_ms?: number | null
}

export type ReviewAction = 'yes' | 'no'
export type ReviewCandidateStatusFilter = 'pending' | 'finished' | 'all'

export interface RelationshipCandidate {
  id: string
  job_id: string
  source_node: string
  target_node: string
  relationship_type: string
  source_chunk_id: string
  source_chunk_name?: string | null
  source_chunk_description?: string | null
  source_chunk_summary?: string | null
  source_chunk_text?: string | null
  source_chunk_label?: string | null
  target_chunk_id?: string | null
  target_chunk_name?: string | null
  target_chunk_description?: string | null
  target_chunk_summary?: string | null
  target_chunk_text?: string | null
  target_chunk_label?: string | null
  evidence_chunk_name?: string | null
  evidence_chunk_description?: string | null
  evidence_text: string
  rationale: string
  review_action?: string | null
  review_note?: string | null
  reviewed_at?: string | null
  reviewer?: string | null
  status: string
  version: number
  metadata: Record<string, unknown>
}

export interface ReviewDecisionRequest {
  action: ReviewAction
  note?: string | null
  reviewer?: string
}

export interface ReviewJobDecision {
  candidate_id: string
  action: ReviewAction
  note?: string | null
}

export interface ReviewJobDecisionRequest {
  decisions: ReviewJobDecision[]
  reviewer?: string
}

export interface MemoryDocument {
  exists: boolean
  id?: string | null
  scope: string
  title: string
  content: string
  version: number
  status: string
  author?: string | null
  updated_at?: string | null
  metadata?: Record<string, unknown> | string | null
  evidence_review_note_ids: string[]
  evidence_candidate_ids: string[]
}

export interface MemoryDocumentUpdateRequest {
  content: string
  title?: string
  update_summary?: string
  author?: string
}
