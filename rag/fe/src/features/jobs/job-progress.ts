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

export function getJobPhase(job: FileIngestStatusResponse) {
  return job.current_phase ?? job.current_stage ?? 'received'
}

export function getStagePhase(stage: FileIngestStatusResponse['stages'][number]) {
  return stage.phase ?? stage.stage ?? 'received'
}

export function getJobProgress(job: FileIngestStatusResponse) {
  const currentStage = normalizeStage(getJobPhase(job))
  const stageText = getJobStageText(job)

  if (job.current_task?.status === 'queued') {
    return { stepIndex: 1, label: 'Queued' }
  }
  if (job.completed || currentStage.includes('complete') || isJobReviewComplete(job)) {
    return { stepIndex: 5, label: 'Complete' }
  }
  if (isJobWaitingReview(job)) {
    return { stepIndex: 4, label: 'Waiting review' }
  }
  if (
    currentStage.includes('embedding') ||
    currentStage.includes('chunk') ||
    currentStage.includes('split')
  ) {
    return { stepIndex: 2, label: 'Chunk and embed' }
  }
  if (currentStage.includes('graph') || currentStage.includes('candidate')) {
    return { stepIndex: 3, label: 'Graph builder' }
  }
  if (
    currentStage.includes('uploaded') ||
    currentStage.includes('stored') ||
    currentStage.includes('index')
  ) {
    return { stepIndex: 1, label: 'Queued' }
  }
  if (stageText.includes('embedding') || stageText.includes('chunk') || stageText.includes('split')) {
    return { stepIndex: 2, label: 'Chunk and embed' }
  }
  if (stageText.includes('graph') || stageText.includes('candidate')) {
    return { stepIndex: 3, label: 'Graph builder' }
  }

  return { stepIndex: 1, label: 'Queued' }
}

export function getJobRuntimeStatus(job: FileIngestStatusResponse): JobRuntimeStatus {
  const currentStage = normalizeStage(getJobPhase(job))
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
  if (job.completed || stageText.includes('complete') || isJobReviewComplete(job)) {
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

export type JobTaskTiming = {
  detailLabel: string
  finishedLabel: string
  isLive: boolean
  primaryLabel: string
  queueWaitLabel: string
  runtimeLabel: string
  startedLabel: string
  totalLabel: string
}

export function getJobTaskTiming(
  job: FileIngestStatusResponse,
  nowMs = Date.now(),
): JobTaskTiming {
  const task = job.current_task
  const submittedMs = parseTimeMs(task?.submitted_at)
  const startedMs = parseTimeMs(task?.started_at)
  const finishedMs = parseTimeMs(task?.finished_at)
  const runtimeStatus = getJobRuntimeStatus(job)
  const endMs = finishedMs ?? nowMs

  const queueWaitMs = submittedMs && startedMs ? Math.max(0, startedMs - submittedMs) : null
  const runtimeMs = startedMs ? Math.max(0, endMs - startedMs) : null
  const totalMs = submittedMs ? Math.max(0, endMs - submittedMs) : null
  const isLive = Boolean(task && !finishedMs && (runtimeStatus === 'queued' || runtimeStatus === 'running'))

  const queueWaitLabel = queueWaitMs === null ? 'Not picked up' : formatDuration(queueWaitMs)
  const runtimeLabel = runtimeMs === null ? 'Not started' : formatDuration(runtimeMs)
  const totalLabel = totalMs === null ? 'No task clock' : formatDuration(totalMs)
  const startedLabel = startedMs ? formatTime(startedMs) : 'Waiting'
  const finishedLabel = finishedMs ? formatTime(finishedMs) : isLive ? 'Live' : 'Pending'

  if (!task) {
    return {
      detailLabel: 'No task clock',
      finishedLabel,
      isLive: false,
      primaryLabel: 'No timer',
      queueWaitLabel,
      runtimeLabel,
      startedLabel,
      totalLabel,
    }
  }

  if (runtimeStatus === 'queued' && submittedMs) {
    return {
      detailLabel: 'waiting in queue',
      finishedLabel,
      isLive,
      primaryLabel: `Queued ${formatDuration(Math.max(0, nowMs - submittedMs))}`,
      queueWaitLabel,
      runtimeLabel,
      startedLabel,
      totalLabel,
    }
  }

  if (runtimeStatus === 'running') {
    return {
      detailLabel: startedMs ? `picked ${startedLabel}` : 'pickup pending',
      finishedLabel,
      isLive,
      primaryLabel: `Run ${runtimeLabel}`,
      queueWaitLabel,
      runtimeLabel,
      startedLabel,
      totalLabel,
    }
  }

  if (runtimeStatus === 'needs_retry') {
    return {
      detailLabel: `failed after ${runtimeLabel}`,
      finishedLabel,
      isLive,
      primaryLabel: `Fail ${runtimeLabel}`,
      queueWaitLabel,
      runtimeLabel,
      startedLabel,
      totalLabel,
    }
  }

  return {
    detailLabel: `queue ${queueWaitLabel}`,
    finishedLabel,
    isLive,
    primaryLabel: `Task ${runtimeLabel}`,
    queueWaitLabel,
    runtimeLabel,
    startedLabel,
    totalLabel,
  }
}

export function isJobWaitingReview(job: FileIngestStatusResponse) {
  const pendingReviewCount = readFiniteNumber(job.pending_review_count)
  if (pendingReviewCount !== null) {
    return pendingReviewCount > 0
  }

  return normalizeStage(getJobPhase(job)).includes('pending_review')
}

function isJobReviewComplete(job: FileIngestStatusResponse) {
  const pendingReviewCount = readFiniteNumber(job.pending_review_count)
  if (pendingReviewCount !== 0) {
    return false
  }

  const currentStage = normalizeStage(getJobPhase(job))
  return currentStage.includes('pending_review') || (job.candidate_count ?? 0) > 0
}

function readFiniteNumber(value: number | undefined) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

export function isPipelineStepDone(job: FileIngestStatusResponse, step: PipelineStepKey) {
  const stepIndex = getJobProgress(job).stepIndex
  const targetIndex = {
    chunked: 2,
    complete: 5,
    built: 3,
    review: 4,
    staged: 1,
  } satisfies Record<PipelineStepKey, number>

  return stepIndex >= targetIndex[step]
}

export function formatStageName(stage: string) {
  return stage.replaceAll('_', ' ')
}

function getJobStageText(job: FileIngestStatusResponse) {
  return [
    getJobPhase(job),
    ...job.stages.flatMap((stage) => [getStagePhase(stage), stage.status, stage.message]),
  ]
    .map(normalizeStage)
    .join(' ')
}

function normalizeStage(stage: string | null | undefined) {
  if (!stage) {
    return ''
  }

  return stage.trim().toLowerCase()
}

function parseTimeMs(value: string | null | undefined) {
  if (!value) {
    return null
  }
  const timestamp = new Date(value).getTime()
  return Number.isNaN(timestamp) ? null : timestamp
}

function formatDuration(durationMs: number) {
  const totalSeconds = Math.max(0, Math.floor(durationMs / 1000))
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds.toString().padStart(2, '0')}s`
  }
  return `${seconds}s`
}

function formatTime(timestampMs: number) {
  return new Intl.DateTimeFormat('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(timestampMs))
}
