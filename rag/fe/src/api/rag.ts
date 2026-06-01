import type {
  CreateDocumentIngestJobRequest,
  FileIngestStatusResponse,
  RagDocument,
  ReviewDecisionRequest,
  ReviewCandidateResponse,
} from '@/types'
import {
  createMockIngestJob,
  getMockDocuments,
  getMockReviewCandidates,
  startMockGraphAdd,
  submitMockReviewDecision,
} from '@/api/mock-data'
import { retrieve } from '@/api/retrieve'

export async function listDocuments(): Promise<RagDocument[]> {
  return retrieve<RagDocument[]>({
    path: '/api/documents',
    mock: getMockDocuments,
  })
}

export async function createIngestJob(
  payload: CreateDocumentIngestJobRequest,
): Promise<FileIngestStatusResponse> {
  return retrieve<FileIngestStatusResponse>({
    path: '/api/ingest/jobs',
    init: {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    mock: () => createMockIngestJob(payload),
  })
}

export async function startGraphAdd(jobId: string): Promise<FileIngestStatusResponse> {
  return retrieve<FileIngestStatusResponse>({
    path: `/api/ingest/jobs/${jobId}/start`,
    init: {
      method: 'POST',
    },
    mock: () => startMockGraphAdd(jobId),
  })
}

export async function listReviewCandidates(): Promise<ReviewCandidateResponse> {
  return retrieve<ReviewCandidateResponse>({
    path: '/api/review/edge-candidates',
    mock: getMockReviewCandidates,
  })
}

export async function submitReviewDecision(
  candidateId: string,
  payload: ReviewDecisionRequest,
): Promise<FileIngestStatusResponse> {
  return retrieve<FileIngestStatusResponse>({
    path: `/api/review/edge-candidates/${encodeURIComponent(candidateId)}/decision`,
    init: {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    mock: () => submitMockReviewDecision(candidateId, payload),
  })
}
