import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import {
  createIngestJob,
  getGlobalMemory,
  listDocuments,
  listIngestJobs,
  listReviewCandidates,
  startGraphAdd,
  submitReviewDecision,
  submitReviewJobDecisions,
  updateGlobalMemory,
} from '@/api/rag'
import {
  hasMockFallback,
  resetMockFallbackState,
} from '@/api/retrieve'
import { normalizeReviewCandidates } from '@/features/review/review-candidates'
import { RagWorkspaceContext } from '@/features/workspace/rag-workspace-context'
import type {
  FileIngestStatusResponse,
  MemoryDocument,
  MemoryDocumentUpdateRequest,
  RagDocument,
  RelationshipCandidate,
  ReviewAction,
  ReviewJobDecision,
} from '@/types'
import type { RagWorkspaceContextValue } from '@/features/workspace/rag-workspace-context'
import type {
  WorkspaceRefreshOptions,
  WorkspaceStatus,
} from '@/features/workspace/rag-workspace-context'

type RagWorkspaceProviderProps = {
  children: ReactNode
}

export function RagWorkspaceProvider({ children }: RagWorkspaceProviderProps) {
  const [documents, setDocuments] = useState<RagDocument[]>([])
  const [jobs, setJobs] = useState<FileIngestStatusResponse[]>([])
  const [reviewCandidates, setReviewCandidates] = useState<RelationshipCandidate[]>([])
  const [memory, setMemory] = useState<MemoryDocument | null>(null)
  const [status, setStatus] = useState<WorkspaceStatus>('idle')
  const [message, setMessage] = useState('Connect to RAG backend and review graph updates.')

  const syncWorkspace = useCallback(async (
    extraJobs: FileIngestStatusResponse[] = [],
    options: WorkspaceRefreshOptions = {},
  ) => {
    if (!options.silent) {
      setStatus('loading')
    }

    try {
      resetMockFallbackState()

      const [nextDocuments, nextJobs, reviewResponse, nextMemory] = await Promise.all([
        listDocuments(),
        listIngestJobs(),
        listReviewCandidates(),
        getGlobalMemory(),
      ])
      const nextReviewCandidates = normalizeReviewCandidates(reviewResponse)
      const inferredJobs = inferJobsFromDocuments(nextDocuments)

      setDocuments(nextDocuments)
      setReviewCandidates(nextReviewCandidates)
      setMemory(nextMemory)
      setJobs((currentJobs) => mergeJobs(currentJobs, inferredJobs, extraJobs, nextJobs))
      if (!options.silent) {
        setStatus('idle')
        setMessage(
          hasMockFallback()
            ? 'RAG backend is unavailable. Showing mock workspace data.'
            : 'RAG backend is connected.',
        )
      }
    } catch (error) {
      console.error('Failed to refresh RAG workspace.', error)
      setStatus('error')
      setMessage('RAG workspace sync failed. Check backend availability.')
    }
  }, [])

  const refreshWorkspace = useCallback(
    (options?: WorkspaceRefreshOptions) => syncWorkspace([], options),
    [syncWorkspace],
  )

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void syncWorkspace()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [syncWorkspace])

  const stageDocument = useCallback(
    async (fileName: string, content: string) => {
      setStatus('loading')

      try {
        const job = await createIngestJob({
          content,
          content_type: inferContentType(fileName),
          file_name: fileName,
        })

        setJobs((currentJobs) => mergeJobs([job], currentJobs))
        await syncWorkspace([job])
      } catch (error) {
        console.error('Failed to stage RAG document.', error)
        setStatus('error')
        setMessage('Document staging failed. Check backend availability.')
      }
    },
    [syncWorkspace],
  )

  const startGraphAddForJob = useCallback(async (jobId: string) => {
    setStatus('loading')

    try {
      const job = await startGraphAdd(jobId)
      const reviewResponse = await listReviewCandidates()

      setJobs((currentJobs) => mergeJobs([job], currentJobs))
      setReviewCandidates(normalizeReviewCandidates(reviewResponse))
      setStatus('idle')
      setMessage(
        hasMockFallback()
          ? 'RAG backend is unavailable. Showing mock workspace data.'
          : 'Graph job dispatched.',
      )
    } catch (error) {
      console.error('Failed to start graph add job.', error)
      setStatus('error')
      setMessage('Graph job dispatch failed. Check backend availability.')
    }
  }, [])

  const submitReviewDecisionForCandidate = useCallback(
    async (
      candidateId: string,
      action: Extract<ReviewAction, 'yes' | 'no'>,
      note: string,
    ) => {
      setStatus('loading')

      try {
        const job = await submitReviewDecision(candidateId, {
          action,
          note: note || null,
          reviewer: 'rag-fe',
        })
        const reviewResponse = await listReviewCandidates()

        setReviewCandidates(normalizeReviewCandidates(reviewResponse))
        setJobs((currentJobs) => mergeJobs([job], currentJobs))
        setStatus('idle')
        setMessage('Review decision submitted.')
      } catch (error) {
        console.error('Failed to submit review decision.', error)
        setStatus('error')
        setMessage('Review decision failed. Check backend availability.')
      }
    },
    [],
  )

  const submitReviewDecisionsForJob = useCallback(
    async (
      jobId: string,
      decisions: ReviewJobDecision[],
    ) => {
      if (decisions.length === 0) {
        return
      }

      setStatus('loading')

      try {
        const job = await submitReviewJobDecisions(jobId, {
          decisions,
          reviewer: 'rag-fe',
        })
        const reviewResponse = await listReviewCandidates()

        setReviewCandidates(normalizeReviewCandidates(reviewResponse))
        setJobs((currentJobs) => mergeJobs([job], currentJobs))
        setStatus('idle')
        setMessage('Review decisions submitted.')
      } catch (error) {
        console.error('Failed to submit review decisions.', error)
        setStatus('error')
        setMessage('Review decisions failed. Check backend availability.')
      }
    },
    [],
  )

  const saveMemory = useCallback(async (request: MemoryDocumentUpdateRequest) => {
    setStatus('loading')

    try {
      const nextMemory = await updateGlobalMemory({
        author: 'rag-fe-memory-settings',
        ...request,
      })
      setMemory(nextMemory)
      setStatus('idle')
      setMessage('Agent memory updated.')
    } catch (error) {
      console.error('Failed to save agent memory.', error)
      setStatus('error')
      setMessage('Agent memory save failed. Check backend availability.')
      throw error
    }
  }, [])

  const pendingReviewCount = useMemo(() => {
    if (reviewCandidates.length > 0) {
      return reviewCandidates.filter(isPendingReviewCandidate).length
    }

    return jobs.reduce((total, job) => total + (job.pending_review_count ?? 0), 0)
  }, [jobs, reviewCandidates])
  const latestJob = jobs[0] ?? null
  const value = useMemo<RagWorkspaceContextValue>(
    () => ({
      documents,
      jobs,
      latestJob,
      memory,
      message,
      pendingReviewCount,
      refresh: refreshWorkspace,
      reviewCandidates,
      saveMemory,
      stageDocument,
      startGraphAddForJob,
      status,
      submitReviewDecisionForCandidate,
      submitReviewDecisionsForJob,
    }),
    [
      documents,
      jobs,
      latestJob,
      memory,
      message,
      pendingReviewCount,
      reviewCandidates,
      saveMemory,
      stageDocument,
      startGraphAddForJob,
      status,
      submitReviewDecisionForCandidate,
      submitReviewDecisionsForJob,
      refreshWorkspace,
    ],
  )

  return (
    <RagWorkspaceContext.Provider value={value}>
      {children}
    </RagWorkspaceContext.Provider>
  )
}

function inferJobsFromDocuments(documents: RagDocument[]): FileIngestStatusResponse[] {
  return documents
    .filter((document) => document.job_id)
    .map((document) => ({
      job_id: document.job_id as string,
      file_name: document.file_name,
      current_phase: 'uploaded_to_database',
      current_stage: 'uploaded_to_database',
      completed: false,
      created_at: document.created_at,
      updated_at: document.updated_at ?? document.indexed_at,
      stages: [
        {
          phase: 'uploaded_to_database',
          stage: 'uploaded_to_database',
          status: 'success',
          message: 'Document is available in the RAG workspace.',
        },
      ],
      document_id: document.document_id,
      chunk_count: 0,
      candidate_count: 0,
      pending_review_count: 0,
    }))
}

function mergeJobs(...jobGroups: FileIngestStatusResponse[][]) {
  const merged = new Map<string, FileIngestStatusResponse>()

  for (const job of jobGroups.flat()) {
    const existing = merged.get(job.job_id)
    merged.set(job.job_id, existing ? { ...existing, ...job } : job)
  }

  return Array.from(merged.values()).sort(compareJobsByNewestUpdate)
}

function compareJobsByNewestUpdate(
  left: FileIngestStatusResponse,
  right: FileIngestStatusResponse,
) {
  return jobUpdatedTime(right) - jobUpdatedTime(left)
}

function jobUpdatedTime(job: FileIngestStatusResponse) {
  const lastStage = job.stages.at(-1)
  const value =
    job.updated_at ??
    job.completed_at ??
    lastStage?.recorded_at ??
    job.created_at ??
    ''
  const parsed = Date.parse(value)

  return Number.isNaN(parsed) ? 0 : parsed
}

function inferContentType(fileName: string) {
  const extension = fileName.split('.').pop()?.toLowerCase()

  switch (extension) {
    case 'csv':
      return 'text/csv'
    case 'json':
      return 'application/json'
    case 'md':
      return 'text/markdown'
    case 'txt':
      return 'text/plain'
    case 'toon':
      return 'toon'
    default:
      return null
  }
}

function isPendingReviewCandidate(candidate: RelationshipCandidate) {
  return candidate.status.toLowerCase() === 'pending_review'
}
