import { createContext } from 'react'

import type {
  FileIngestStatusResponse,
  MemoryDocument,
  MemoryDocumentUpdateRequest,
  RagDocument,
  RelationshipCandidate,
  ReviewAction,
  ReviewJobDecision,
} from '@/types'

export type WorkspaceStatus = 'idle' | 'loading' | 'error'

export type WorkspaceRefreshOptions = {
  silent?: boolean
}

export type RagWorkspaceContextValue = {
  documents: RagDocument[]
  jobs: FileIngestStatusResponse[]
  latestJob: FileIngestStatusResponse | null
  memory: MemoryDocument | null
  message: string
  pendingReviewCount: number
  refresh: (options?: WorkspaceRefreshOptions) => Promise<void>
  reviewCandidates: RelationshipCandidate[]
  stageDocument: (fileName: string, content: string) => Promise<void>
  startGraphAddForJob: (jobId: string) => Promise<void>
  status: WorkspaceStatus
  saveMemory: (request: MemoryDocumentUpdateRequest) => Promise<void>
  submitReviewDecisionForCandidate: (
    candidateId: string,
    action: Extract<ReviewAction, 'yes' | 'no'>,
    note: string,
  ) => Promise<void>
  submitReviewDecisionsForJob: (
    jobId: string,
    decisions: ReviewJobDecision[],
  ) => Promise<void>
}

export const RagWorkspaceContext = createContext<RagWorkspaceContextValue | null>(null)
