import {
  CheckCircle2,
  Clock3,
  Cpu,
  GitBranch,
  Play,
  Rows3,
  type LucideIcon,
} from 'lucide-react'

import { JobCard } from '@/features/jobs/job-card'
import { PageHeader } from '@/components/workspace/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import {
  formatStageName,
  getJobProgress,
  getJobRuntimeStatus,
  getWorkerGroupLabel,
  isJobWaitingReview,
  type WorkerGroupKey,
} from '@/features/jobs/job-progress'
import { useRagWorkspace } from '@/features/workspace/use-rag-workspace'
import type { FileIngestStatusResponse } from '@/types'

export function GraphJobsPage() {
  const { jobs, latestJob, startGraphAddForJob, status } = useRagWorkspace()
  const runningJobs = jobs.filter((job) => getJobRuntimeStatus(job) === 'running').length
  const queuedJobs = jobs.filter((job) => getJobRuntimeStatus(job) === 'queued').length
  const workerGroupCounts = getWorkerGroupCounts(jobs)
  const pendingReviewCount = jobs.reduce(
    (total, job) => total + (job.pending_review_count ?? 0),
    0,
  )
  const actionableJob =
    jobs.find((job) => !job.completed && !isJobWaitingReview(job)) ?? latestJob
  const actionableProgress = actionableJob ? getJobProgress(actionableJob) : null
  const actionableWorkerGroup = actionableJob ? getWorkerGroupLabel(actionableJob) : null
  const canDispatch = Boolean(actionableJob) && status !== 'loading'

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        title="Graph Jobs"
        description="Track graph-add dispatch, worker groups, and document-level processing progress."
        action={
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{jobs.length} documents</Badge>
            <Badge variant="secondary">{pendingReviewCount} review candidates</Badge>
          </div>
        }
      />

      <div className="grid items-start gap-3 xl:grid-cols-[minmax(0,1.15fr)_minmax(22rem,0.85fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Queue Control</CardTitle>
            <CardDescription>Dispatch the next staged document into graph-add workers.</CardDescription>
            <CardAction>
              <Badge variant={status === 'loading' ? 'outline' : 'secondary'}>
                {status === 'loading' ? 'Syncing' : 'Ready'}
              </Badge>
            </CardAction>
          </CardHeader>
          <CardContent className="grid gap-4">
            {actionableJob && actionableProgress ? (
              <>
                <div className="grid gap-3 rounded-md border bg-muted/30 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{actionableJob.file_name}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {actionableJob.job_id} - {formatStageName(actionableJob.current_stage)}
                      </p>
                    </div>
                    <Badge variant="outline">{actionableProgress.label}</Badge>
                  </div>
                  <div className="grid gap-2">
                    <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                      <span>Document progress</span>
                      <span>{actionableProgress.percent}%</span>
                    </div>
                    <Progress value={actionableProgress.percent} />
                  </div>
                </div>
                <Button
                  type="button"
                  onClick={() => void startGraphAddForJob(actionableJob.job_id)}
                  disabled={!canDispatch}
                >
                  <Play data-icon="inline-start" aria-hidden="true" />
                  Dispatch next graph task
                </Button>
                <div className="grid gap-2 sm:grid-cols-3">
                  <QueueFact label="Worker lane" value={actionableWorkerGroup ?? '-'} />
                  <QueueFact label="Chunks" value={actionableJob.chunk_count ?? 0} />
                  <QueueFact label="Candidates" value={actionableJob.candidate_count ?? 0} />
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">No staged jobs are available.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Worker Groups</CardTitle>
            <CardDescription>Queue pressure by processing lane.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2">
            <WorkerGroupRow
              icon={Rows3}
              label="ingest-workers"
              value={workerGroupCounts['ingest-workers']}
              detail="queued documents"
            />
            <WorkerGroupRow
              icon={Cpu}
              label="chunk-workers"
              value={workerGroupCounts['chunk-workers']}
              detail="active documents"
            />
            <WorkerGroupRow
              icon={GitBranch}
              label="graph-builders"
              value={workerGroupCounts['graph-builders']}
              detail="graph-add jobs"
            />
            <WorkerGroupRow
              icon={Clock3}
              label="review-handoff"
              value={pendingReviewCount}
              detail="candidate decisions"
            />
            <WorkerGroupRow
              icon={CheckCircle2}
              label="archive-sync"
              value={workerGroupCounts['archive-sync']}
              detail="completed documents"
            />
          </CardContent>
        </Card>
      </div>

      <section className="grid gap-3">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold">Document Processing Queue</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Progress is shown per document so parallel workers can be audited independently.
            </p>
          </div>
          <Badge variant="outline">{runningJobs + queuedJobs} active</Badge>
        </div>
        {jobs.map((job) => (
          <JobCard key={job.job_id} job={job} />
        ))}
      </section>
    </div>
  )
}

function getWorkerGroupCounts(jobs: FileIngestStatusResponse[]) {
  const counts: Record<WorkerGroupKey, number> = {
    'ingest-workers': 0,
    'chunk-workers': 0,
    'graph-builders': 0,
    'review-handoff': 0,
    'archive-sync': 0,
  }

  for (const job of jobs) {
    counts[getWorkerGroupLabel(job)] += 1
  }

  return counts
}

function QueueFact({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="min-w-0 rounded-md border bg-background px-3 py-2">
      <p className="truncate text-xs text-muted-foreground">{label}</p>
      <p className="truncate text-sm font-medium">{value}</p>
    </div>
  )
}

function WorkerGroupRow({
  detail,
  icon: Icon,
  label,
  value,
}: {
  detail: string
  icon: LucideIcon
  label: string
  value: number
}) {
  return (
    <div className="flex min-w-0 items-center justify-between gap-3 rounded-md border bg-muted/30 px-3 py-2">
      <div className="flex min-w-0 items-center gap-2">
        <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{label}</p>
          <p className="text-xs text-muted-foreground">{detail}</p>
        </div>
      </div>
      <Badge variant={value > 0 ? 'outline' : 'secondary'}>{value}</Badge>
    </div>
  )
}
