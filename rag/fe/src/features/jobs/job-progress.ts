import type { FileIngestStatusResponse } from '@/types'

export type PipelineStepKey = 'staged' | 'chunked' | 'built' | 'review' | 'complete'

export type PipelineStep = {
  key: PipelineStepKey
  label: string
}

export const pipelineSteps: PipelineStep[] = [
  { key: 'staged', label: 'Staged' },
  { key: 'chunked', label: 'Chunked' },
  { key: 'built', label: 'Graph built' },
  { key: 'review', label: 'Review' },
  { key: 'complete', label: 'Complete' },
]

export type JobRuntimeStatus = 'queued' | 'running' | 'waiting_review' | 'complete' | 'needs_retry'

export type WorkerGroupKey =
  | 'ingest-workers'
  | 'chunk-workers'
  | 'graph-builders'
  | 'review-handoff'
  | 'archive-sync'

export function getJobProgress(job: FileIngestStatusResponse) {
  const currentStage = normalizeStage(job.current_stage)
  const stageText = getJobStageText(job)

  if (job.current_task?.status === 'queued') {
    return { percent: 24, label: 'Queued' }
  }
  if (job.completed || currentStage.includes('complete')) {
    return { percent: 100, label: 'Complete' }
  }
  if (isJobWaitingReview(job)) {
    return { percent: 78, label: 'Waiting review' }
  }
  if (
    currentStage.includes('embedding') ||
    currentStage.includes('chunk') ||
    currentStage.includes('split')
  ) {
    return { percent: 46, label: 'Chunk and embed' }
  }
  if (currentStage.includes('graph') || currentStage.includes('candidate')) {
    return { percent: 62, label: 'Graph builder' }
  }
  if (
    currentStage.includes('uploaded') ||
    currentStage.includes('stored') ||
    currentStage.includes('index')
  ) {
    return { percent: 24, label: 'Queued' }
  }
  if (stageText.includes('embedding') || stageText.includes('chunk') || stageText.includes('split')) {
    return { percent: 46, label: 'Chunk and embed' }
  }
  if (stageText.includes('graph') || stageText.includes('candidate')) {
    return { percent: 62, label: 'Graph builder' }
  }

  return { percent: 8, label: 'Queued' }
}

export function getJobRuntimeStatus(job: FileIngestStatusResponse): JobRuntimeStatus {
  const currentStage = normalizeStage(job.current_stage)
  const stageText = getJobStageText(job)

  if (job.current_task?.status === 'queued') {
    return 'queued'
  }
  if (job.current_task?.status === 'running') {
    return 'running'
  }
  if (job.current_task?.status === 'failed') {
    return 'needs_retry'
  }
  if (job.completed || stageText.includes('complete')) {
    return 'complete'
  }
  if (stageText.includes('retry') || stageText.includes('error') || stageText.includes('failed')) {
    return 'needs_retry'
  }
  if (isJobWaitingReview(job)) {
    return 'waiting_review'
  }
  if (
    currentStage.includes('graph') ||
    currentStage.includes('chunk') ||
    currentStage.includes('embedding') ||
    currentStage.includes('worker') ||
    stageText.includes('running')
  ) {
    return 'running'
  }

  return 'queued'
}

export function getRuntimeStatusLabel(status: JobRuntimeStatus) {
  switch (status) {
    case 'complete':
      return 'Complete'
    case 'needs_retry':
      return 'Needs retry'
    case 'running':
      return 'Running'
    case 'waiting_review':
      return 'Waiting review'
    case 'queued':
      return 'Queued'
  }
}

export function getWorkerGroupLabel(job: FileIngestStatusResponse): WorkerGroupKey {
  const currentStage = normalizeStage(job.current_stage)
  const stageText = getJobStageText(job)

  if (job.completed) {
    return 'archive-sync'
  }
  if (isJobWaitingReview(job)) {
    return 'review-handoff'
  }
  if (currentStage.includes('graph') || currentStage.includes('candidate')) {
    return 'graph-builders'
  }
  if (currentStage.includes('chunk') || currentStage.includes('embedding')) {
    return 'chunk-workers'
  }
  if (stageText.includes('running') && stageText.includes('embedding')) {
    return 'chunk-workers'
  }

  return 'ingest-workers'
}

export function isJobWaitingReview(job: FileIngestStatusResponse) {
  return (
    (job.pending_review_count ?? 0) > 0 ||
    normalizeStage(job.current_stage).includes('pending_review')
  )
}

export function isPipelineStepDone(job: FileIngestStatusResponse, step: PipelineStepKey) {
  const progress = getJobProgress(job).percent

  switch (step) {
    case 'staged':
      return progress >= 24
    case 'chunked':
      return progress >= 46
    case 'built':
      return progress >= 62
    case 'review':
      return progress >= 78
    case 'complete':
      return progress >= 100
  }
}

export function formatStageName(stage: string) {
  return stage.replaceAll('_', ' ')
}

function getJobStageText(job: FileIngestStatusResponse) {
  return [
    job.current_stage,
    ...job.stages.flatMap((stage) => [stage.stage, stage.status, stage.message]),
  ]
    .map(normalizeStage)
    .join(' ')
}

function normalizeStage(stage: string) {
  return stage.trim().toLowerCase()
}
