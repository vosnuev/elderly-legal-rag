import type {
  CreateDocumentIngestJobRequest,
  FileIngestStatusResponse,
  MemoryDocument,
  MemoryDocumentUpdateRequest,
  RagDocument,
  ReviewDecisionRequest,
  ReviewCandidateResponse,
  ReviewCandidateStatusFilter,
  ReviewJobDecisionRequest,
} from '@/types'
import {
  createMockIngestJob,
  getMockDocuments,
  getMockJobs,
  getMockReviewCandidates,
  startMockGraphAdd,
  submitMockReviewDecision,
  submitMockReviewJobDecisions,
  getMockMemory,
  updateMockMemory,
} from '@/api/mock-data'
import { retrieve } from '@/api/retrieve'

const REVIEW_CANDIDATE_PAGE_LIMIT = 100

type ReviewCandidateListOptions = {
  documentId?: string
  jobId?: string
}

export async function listDocuments(): Promise<RagDocument[]> {
  return retrieve<RagDocument[]>({
    path: '/api/documents',
    mock: getMockDocuments,
  })
}

export async function listIngestJobs(limit = 50): Promise<FileIngestStatusResponse[]> {
  const jobs = await retrieve<FileIngestStatusResponse[]>({
    path: `/api/ingest/jobs?limit=${limit}`,
    mock: getMockJobs,
  })

  return jobs.map(normalizeIngestJob)
}

export async function createIngestJob(
  payload: CreateDocumentIngestJobRequest,
): Promise<FileIngestStatusResponse> {
  const job = await retrieve<FileIngestStatusResponse>({
    path: '/api/ingest/jobs',
    init: {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    mock: () => createMockIngestJob(payload),
  })

  return normalizeIngestJob(job)
}

export async function startGraphAdd(jobId: string): Promise<FileIngestStatusResponse> {
  const job = await retrieve<FileIngestStatusResponse>({
    path: `/api/ingest/jobs/${jobId}/start`,
    init: {
      method: 'POST',
    },
    mock: () => startMockGraphAdd(jobId),
  })

  return normalizeIngestJob(job)
}

export async function listReviewCandidates(
  status: ReviewCandidateStatusFilter = 'all',
  options: ReviewCandidateListOptions = {},
): Promise<ReviewCandidateResponse> {
  if (status === 'all') {
    const [pendingResponse, finishedResponse] = await Promise.all([
      fetchReviewCandidates('pending', options),
      fetchReviewCandidates('finished', options),
    ])

    return mergeReviewCandidateResponses(pendingResponse, finishedResponse)
  }

  return fetchReviewCandidates(status, options)
}

async function fetchReviewCandidates(
  status: Exclude<ReviewCandidateStatusFilter, 'all'>,
  options: ReviewCandidateListOptions,
): Promise<ReviewCandidateResponse> {
  const searchParams = new URLSearchParams({
    limit: String(REVIEW_CANDIDATE_PAGE_LIMIT),
    status,
  })
  if (options.jobId) {
    searchParams.set('job_id', options.jobId)
  }
  if (options.documentId) {
    searchParams.set('document_id', options.documentId)
  }

  return retrieve<ReviewCandidateResponse>({
    path: `/api/review/edge-candidates?${searchParams.toString()}`,
    mock: () => getMockReviewCandidates(status),
  })
}

function mergeReviewCandidateResponses(
  ...responses: ReviewCandidateResponse[]
): ReviewCandidateResponse {
  const seenIds = new Set<string>()
  const rows: unknown[] = []

  responses.forEach((response) => {
    const responseRows = response.rows ?? []
    responseRows.forEach((row) => {
      const candidateId = readCandidateId(row)
      if (candidateId && seenIds.has(candidateId)) {
        return
      }
      if (candidateId) {
        seenIds.add(candidateId)
      }
      rows.push(row)
    })
  })

  return {
    columns: responses.find((response) => response.columns?.length)?.columns,
    elapsed_ms: responses.reduce((total, response) => total + (response.elapsed_ms ?? 0), 0),
    row_count: rows.length,
    rows,
  }
}

function readCandidateId(row: unknown): string | null {
  if (Array.isArray(row)) {
    return readCandidateId(row[0])
  }
  if (!row || typeof row !== 'object') {
    return null
  }

  const record = row as Record<string, unknown>
  const candidateValue =
    record.candidate ??
    record.relationship_candidate ??
    record.rc ??
    record.properties ??
    record

  if (!candidateValue || typeof candidateValue !== 'object') {
    return null
  }

  const candidate = candidateValue as Record<string, unknown>
  const properties = (
    candidate.properties && typeof candidate.properties === 'object'
      ? candidate.properties
      : candidate
  ) as Record<string, unknown>
  const id = properties.id ?? properties.candidate_id

  return typeof id === 'string' && id.trim() ? id : null
}

export async function submitReviewDecision(
  candidateId: string,
  payload: ReviewDecisionRequest,
): Promise<FileIngestStatusResponse> {
  const job = await retrieve<FileIngestStatusResponse>({
    path: `/api/review/edge-candidates/${encodeURIComponent(candidateId)}/decision`,
    init: {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    mock: () => submitMockReviewDecision(candidateId, payload),
  })

  return normalizeIngestJob(job)
}

export async function submitReviewJobDecisions(
  jobId: string,
  payload: ReviewJobDecisionRequest,
): Promise<FileIngestStatusResponse> {
  const job = await retrieve<FileIngestStatusResponse>({
    path: `/api/review/jobs/${encodeURIComponent(jobId)}/decisions`,
    init: {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    mock: () => submitMockReviewJobDecisions(jobId, payload),
  })

  return normalizeIngestJob(job)
}

export async function getGlobalMemory(): Promise<MemoryDocument> {
  return retrieve<MemoryDocument>({
    path: '/api/memory/global',
    mock: getMockMemory,
  })
}

export async function updateGlobalMemory(
  payload: MemoryDocumentUpdateRequest,
): Promise<MemoryDocument> {
  return retrieve<MemoryDocument>({
    path: '/api/memory/global',
    init: {
      method: 'PUT',
      body: JSON.stringify(payload),
    },
    mock: () => updateMockMemory(payload),
  })
}

function normalizeIngestJob(job: FileIngestStatusResponse): FileIngestStatusResponse {
  const currentPhase = job.current_phase ?? job.current_stage ?? 'received'

  return {
    ...job,
    current_phase: currentPhase,
    current_stage: currentPhase,
    stages: (job.stages ?? []).map(normalizeIngestStage),
  }
}

function normalizeIngestStage(stage: FileIngestStatusResponse['stages'][number]) {
  const phase = stage.phase ?? stage.stage ?? 'received'

  return {
    ...stage,
    phase,
    stage: phase,
  }
}
