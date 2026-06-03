export interface CreateDocumentIngestJobRequest {
  file_name: string
  content: string
  content_type?: string | null
}

export interface IngestStageResult {
  stage: string
  status: string
  message: string
  path?: string | null
  error?: string | null
}

export interface FileIngestStatusResponse {
  job_id: string
  file_name: string
  current_stage: string
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
  elapsed_ms?: number
}

export type ReviewAction = 'yes' | 'no' | 'retry'

export interface RelationshipCandidate {
  id: string
  job_id: string
  source_node: string
  target_node: string
  relationship_type: string
  source_chunk_id: string
  evidence_text: string
  rationale: string
  status: string
  version: number
  metadata: Record<string, unknown>
}

export interface ReviewDecisionRequest {
  action: ReviewAction
  note?: string | null
  reviewer?: string
}

export interface IngestGraphResult {
  job_id: string
  phase: string
  document_id?: string | null
  chunk_count: number
  candidate_count: number
  pending_review_count: number
  warnings: string[]
  errors: string[]
}
