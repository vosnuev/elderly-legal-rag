import { createContext } from 'react'

import type {
  FileIngestStatusResponse,
  RagDocument,
  RelationshipCandidate,
  ReviewAction,
} from '@/types'

export type WorkspaceStatus = 'idle' | 'loading' | 'error'

export type RagWorkspaceContextValue = {
  documents: RagDocument[]
  jobs: FileIngestStatusResponse[]
  latestJob: FileIngestStatusResponse | null
  message: string
  pendingReviewCount: number
  refresh: () => Promise<void>
  reviewCandidates: RelationshipCandidate[]
  stageDocument: (fileName: string, content: string) => Promise<void>
  startGraphAddForJob: (jobId: string) => Promise<void>
  status: WorkspaceStatus
  submitReviewDecisionForCandidate: (
    candidateId: string,
    action: Extract<ReviewAction, 'yes' | 'no'>,
    note: string,
  ) => Promise<void>
}

export const RagWorkspaceContext = createContext<RagWorkspaceContextValue | null>(null)
