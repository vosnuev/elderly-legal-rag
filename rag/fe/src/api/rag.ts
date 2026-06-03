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
): Promise<ReviewCandidateResponse> {
  const searchParams = new URLSearchParams({ status })

  return retrieve<ReviewCandidateResponse>({
    path: `/api/review/edge-candidates?${searchParams.toString()}`,
    mock: () => getMockReviewCandidates(status),
  })
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
